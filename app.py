from flask import Flask, render_template
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def loginpage():
    return render_template('frontpage.html')

@app.route('/logout')
def logOut():
    return render_template('logout.html')

if __name__ == '__main__':
    app.run(debug=True)

    