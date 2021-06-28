from flask import Flask, render_template, redirect, request, session
import pyrebase
from werkzeug.utils import secure_filename
import uuid
import json
from pymongo import MongoClient
import datetime
import os

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
        userposts = posts[session['user'][0]]
        img = userposts.find({})
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
        return render_template('user home.html', images = data, user = session['user'][0], total=total, pic=pfp)
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
        print(user)
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
    
    try:
        if password == conpassword:
            detailsifany = accounts.find_one({"email":email})
            if detailsifany == None:
                nameifany = accounts.find_one({"username":name})
                if nameifany == None:
                    user = auth.create_user_with_email_and_password(email, password)
                    print(user)
                    data = {
                        "username": name,
                        "email": email,
                        "password": password
                    }
                    usercollection = socialapp[name]
                    usercollection.insert_one(data)
                    accounts.insert_one(data)
                    session['user'] = [name, email, password]
                    image = os.path.join(os.path.dirname(__file__), "static\\user.png")
                    storage.child(f"users/{session['user'][0]}/Info/ProfilePic.png").put(image)          
                    return redirect('/')
                else:
                    return "Username Already Exist!"
            else:
                return "Email Already Exist!"
        else:
            return "passwords doesn't match!"
    except:
        return "Error (weak password)"

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

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'GET':
        return render_template('settings.html')
    else:
        file = request.files['image']
        storage.child(f"users/{session['user'][0]}/Info/ProfilePic.png").put(file)
        return redirect("/")
    
@app.route('/logout')
def logout():
    session.pop('user')
    return redirect('/')

@app.route('/user/<string:name>')
def users(name):
    nameifany = accounts.find_one({"username":name})
    if nameifany != None:
        if 'user' in session:
            if name == session['user'][0]:
                return redirect('/')
            else:
                userposts = posts[name]
                img = userposts.find({})
                data = []
                total = 0
                for image in img:
                    total+=1
                    data.append({"ID": image['_id'], "link": image['url'], "text": image['text'], "date": image['date'], "time": image['time']})
                # print(data)
                pfp = storage.child(f"users/{name}/Info/ProfilePic.png").get_url(None)  
                return render_template('profiles.html', images = data, user = name, total=total, pic=pfp)
        else:
            return redirect('/login')
    else:
        return f"{name} account doesn't exist!"
    # return "e"
    
if __name__ == '__main__':
    app.run('localhost', 8080, True)