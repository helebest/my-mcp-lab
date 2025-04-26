from flask import Flask, redirect, url_for, session
from authlib.integrations.flask_client import OAuth
import os

app = Flask(__name__)
app.secret_key = 'fsadfaxiadfo#!'  # 请替换为您的密钥

# 配置 OAuth
oauth = OAuth(app)
oauth.register(
    name='github',
    client_id='Ov23liuISbdburGixBQE',
    client_secret='',
    access_token_url='https://github.com/login/oauth/access_token',
    authorize_url='https://github.com/login/oauth/authorize',
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'user:email'},
)

@app.route('/')
def homepage():
    return '欢迎访问，<a href="/login">使用 GitHub 登录</a>'

@app.route('/login')
def login():
    github = oauth.create_client('github')
    redirect_uri = url_for('authorize', _external=True)
    return github.authorize_redirect(redirect_uri)

@app.route('/authorize')
def authorize():
    github = oauth.create_client('github')
    token = github.authorize_access_token()
    resp = github.get('user')
    user_info = resp.json()
    # 在此处，您可以将用户信息存储到数据库中
    print(user_info['email'])
    return f'您好，{user_info["login"]}！'

if __name__ == '__main__':
    app.run(port=8181, debug=True)