from flask import Flask, render_template, redirect, request, session, abort
import pyrebase
from werkzeug.utils import secure_filename
import uuid
import pathlib
import json
from pymongo import MongoClient
import datetime
import os
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
from flask_cors import CORS
import google.auth.transport.requests
import requests

#-----------------------------------private stuff--------------------------

with open("cred.json", "r") as f:
    credentials = json.load(f)

with open("creds.json", "r") as f:
    keys = json.load(f)

GOOGLE_CLIENT_ID = credentials['GOOGLE_CLIENT_ID']
client_secrets_file = os.path.join(pathlib.Path(__file__).parent, "creds.json")
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
flow = Flow.from_client_secrets_file(
    client_secrets_file=client_secrets_file,
    scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"],
    redirect_uri="http://127.0.0.1:5000/callback"
)


def login_is_required(function):
    def wrapper(*args, **kwargs):
        if "google_id" not in session:
            return abort(401)  # Authorization required
        else:
            return function()

    return wrapper

creds = credentials['creds']
db = MongoClient(credentials['mongo'])
socialapp = db['Users']
accounts = socialapp['Users']
posts = db['Posts']
RAdb = db['RAdb']
firebase = pyrebase.initialize_app(creds)
db = firebase.database()
auth = firebase.auth()
storage = firebase.storage()
app = Flask(__name__)
app.config['SECRET_KEY'] = credentials['sessionkey']

limiter = Limiter(
    app,
    key_func=get_remote_address
)

#----------------------------------------------------------------------------
@app.route('/')
def index():
    posts = RAdb['posts'].find({})
    if 'user' in session:
        return render_template('browse.html', posts=posts)
    else:
        return render_template('browse no user.html', posts=posts)        
@app.route('/profile')
def home():
    if 'user' in session:
        img = RAdb['posts'].find({'by': session['user'][0]})#userposts.find({})
        data = []
        total = 0
        for image in img:
            total+=1
            data.append({"ID": image['_id'], "link": image['url'], "text": image['text'], "date": image['date'], "time": image['time']})
        # print(data)
        try:
            pfp = storage.child(f"users/{session['user'][0]}/Info/ProfilePic.png").get_url(None)
        except:
            image = os.path.join(os.path.dirname(__file__), "static\\user.png")
            storage.child(f"users/{session['user'][0]}/Info/ProfilePic.png").put(image) 
            pfp = storage.child(f"users/{session['user'][0]}/Info/ProfilePic.png").get_url(None)  
        return render_template('user home.html', images = data, user = session['user'][2], total=total, pic=pfp)
    else:
        return render_template('home.html')

@app.route("/login")
def login():
    authorization_url, state = flow.authorization_url()
    session["state"] = state
    return redirect(authorization_url)

@app.route("/callback")
def callback():
    flow.fetch_token(authorization_response=request.url)

    if not session["state"] == request.args["state"]:
        abort(500)  # State does not match!

    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token,
        request=token_request,
        audience=GOOGLE_CLIENT_ID
    )
    email = id_info.get("email")
    name = id_info.get("name")
    # return str([email, name, picture])
    ifExist = accounts.find_one({'email': email})
    if ifExist is not None:
        session['user'] = [ifExist['_id'], email, name]
        return redirect('/profile')
    else:
        ID = str(uuid.uuid4())
        data = {'_id': ID, 'email': email, 'name': name}
        accounts.insert_one(data)
        session['user'] = [ID, email, name]
        image = os.path.join(os.path.dirname(__file__), "static\\user.png")
        storage.child(f"users/{session['user'][0]}/Info/ProfilePic.png").put(image) 
        return redirect('/profile')


@app.route('/upload')
def upload():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_func():
    
    now = datetime.datetime.now()   
    filename = str(uuid.uuid4())
    file = request.files['files']
    text = request.form['text']
    tags = request.form['tags']
    name = file.filename
    taglist = tags.split(" ")
    ext = name.split(".")
    storage.child(f"users/{session['user'][0]}/media/{filename}.{ext[1]}").put(file)
    url = storage.child(f"users/{session['user'][0]}/media").child(f"{filename}.{ext[1]}").get_url(None)
    data = {
        '_id': filename,
        'by' : session['user'][0],
        'name': session['user'][2],
        'url': url, 
        'text': text, 
        'tags': taglist,
        'date': now.strftime("%Y-%m-%d"),
        'time': now.strftime("%H:%M:%S"),
        'comments': [],
        'likes': []
        }
    # collection = posts[session['user'][0]]
    # collection.insert_one(data)
    RAdb['posts'].insert_one(data)
    for tag in taglist:
        TagExist = RAdb['tags'].find_one({'_id': tag})
        if not TagExist:
            RAdb['tags'].insert_one({'_id': tag, 'posts': [filename]})
        else:
            tagposts = TagExist['posts']
            tagposts.append(filename)
            RAdb['tags'].update_one({'_id': tag}, {'$set':{'posts': tagposts}})
    return redirect('/profile')

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'GET':
        return render_template('settings.html')
    else:
        file = request.files['image']
        storage.child(f"users/{session['user'][0]}/Info/ProfilePic.png").put(file)
        return redirect("/profile")
    
@app.route('/logout')
def logout():
    session.pop('user')
    return redirect('/')

@app.route('/user/<string:name>')
def users(name):
    nameifany = accounts.find_one({"_id":name})
    if nameifany != None:
        if 'user' in session:
            if name == session['user'][0]:
                return redirect('/profile')
            else:
                img = RAdb['posts'].find({'by': name})
                data = []
                total = 0
                for image in img:
                    total+=1
                    data.append({"ID": image['_id'], "link": image['url'], "text": image['text'], "date": image['date'], "time": image['time']})
                # print(data)
                pfp = storage.child(f"users/{name}/Info/ProfilePic.png").get_url(None)  
                name = accounts.find_one({'_id': name})
                return render_template('profiles.html', images = data, user = name['name'], total=total, pic=pfp)
        else:
            return redirect('/login')
    else:
        return f"{name} account doesn't exist!"
    # return "e"
@app.route('/post/<string:postID>')
def post(postID):
    # try:
    if 'user' in session:
        post = RAdb['posts'].find_one({'_id': postID})
        user = post['by']
        pfp = storage.child(f"users/{user}/Info/ProfilePic.png").get_url(None) 
        
        return render_template('post.html', data=post, pic=pfp)
    else:
        post = RAdb['posts'].find_one({'_id': postID})
        user = post['by']
        pfp = storage.child(f"users/{user}/Info/ProfilePic.png").get_url(None) 
        
        return render_template('post no user.html', data=post, pic=pfp)
    # except:
    #     return "Post With this ID doesn't exist!"
@app.route('/comment/<string:ID>/')
@limiter.limit("5 per minute")
def commemnt(ID):
    if 'user' in session:
        text = request.args.get('text')
        data = {'by': session['user'][2], 'text': text, 'id': session['user'][0]}
        try:
            comments = RAdb['posts'].find_one({'_id': ID})
            if comments is not None:
                comments = comments['comments']
                comments.append(data)
                RAdb['posts'].update_one({'_id': ID}, {'$set': {'comments': comments}})
                return "Commented!"
            else:
                return "that ID doesn't exist!"
        except:
            return "Failed!"
    else:
        return redirect('/login')
    
@app.route('/TOS')
def tos():
    return render_template('tos.html')

@app.route('/privacy-policy')
def privacypolicy():
    return render_template('privacy-policy.html')
                
if __name__ == '__main__':
    app.run(debug=True)