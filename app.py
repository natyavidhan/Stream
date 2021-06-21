from flask import Flask, render_template, redirect, request, session
import pyrebase
from werkzeug.utils import secure_filename
import uuid
import json
from pymongo import MongoClient
import datetime
#-----------------------------------private stuff--------------------------
with open("cred.json", "r") as f:
    credentials = json.load(f)
    
creds = credentials['creds']
db = MongoClient(credentials['mongo'])
socialapp = db['Users']
accounts = socialapp['users']
posts = db['Posts']
firebase = pyrebase.initialize_app(creds)
db = firebase.database()
auth = firebase.auth()
storage = firebase.storage()
app = Flask(__name__)
app.config['SECRET_KEY'] = credentials['sessionkey']

#----------------------------------------------------------------------------

@app.route('/')
def home():
    if 'user' in session:
        # img = db.order_by_child("users").equal_to(session['user'][0]).get()
        # img = db.child("users").child(session['user'][0]).child('media').get()
        userposts = posts[session['user'][0]]
        img = userposts.find({})
        data = []
        for image in img:
            data.append({"link": image['url'], "text": image['text'], "date": image['date'], "time": image['time']})
        # print(data)
        return render_template('user home.html', images = data, user = session['user'][0])
    else:
        return render_template('home.html')



@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_func():
    email = request.form['user']
    password = request.form['password']
    try:
        user = auth.sign_in_with_email_and_password(email, password)
        # print(user)
        name = accounts.find_one({"email":email})
        username = name['username']
        session['user'] = [username, email, password]
        return redirect('/')
    except:
        return "Wrong Email or/and Password!"
    
    
@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/signup', methods=['POST'])
def signup_func():
    email = request.form['email']
    name = request.form['username']
    password = request.form['password']
    conpassword = request.form['confirmpassword']
    
    # try:
    if password == conpassword:
        detailsifany = accounts.find_one({"email":email})
        if detailsifany == None:
            nameifany = accounts.find_one({"username":name})
            if nameifany == None:
                user = auth.create_user_with_email_and_password(email, password)
                data = {
                    "username": name,
                    "email": email,
                    "password": password
                }
                usercollection = socialapp[name]
                usercollection.insert_one(data)
                accounts.insert_one(data)
                session['user'] = [name, email, password]          
                return redirect('/')
            else:
                return "Username Already Exist!"
        else:
            return "Email Already Exist!"
    else:
        return "passwords doesn't match!"
    # except:
    #     return "Error (weak password)"

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
        'url': url, 
        'text': text, 
        'tags': taglist,
        'date': now.strftime("%Y-%m-%d"),
        'time': now.strftime("%H:%M:%S"),
        'comments': {},
        'likes': []
        }
    collection = posts[session['user'][0]]
    collection.insert_one(data)
    return redirect('/')

@app.route('/logout')
def logout():
    session.pop('user')
    return redirect('/')

@app.route('/user/<string:name>')
def users(name):
    usernames = db.child("users").get()
    if name in usernames.val():
        img = db.child("users").child(name).child('media').get()
        data = []
        if img.val() == None:
            return render_template('user home.html', images = data)
        else:
            for image in img.val():
                mages = db.child("users").child(name).child('media').child(image).get().val()
                data.append({"link": mages['url'], "text": mages['text']})
                print(f"image link: {mages['url']} \nText: {mages['text']}")
                
    else:
        return f"{name} account doesn't exist!"
    # return "e"
if __name__ == '__main__':
    app.run('localhost', 8080, True)