__author__ = 'Suraj'

from flask import Flask, render_template, url_for, request, redirect, flash, jsonify
from flask import session as login_session
import random, string
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Base, Restaurant, MenuItem, User

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

from functools import wraps

# Connect to database and create a database session object
engine = create_engine('sqlite:///restaurantmenuwithusers.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Restaurant Menu Application"

def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    login_session['user_id'] = user.id
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None



@app.route('/login')
def showLogin():
    # Create anti forgery state token
    state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(32))
    login_session['state'] = state
    # return "The current session state is {}".format(login_session['state'])
    return render_template('login.html', client_id=CLIENT_ID, STATE=state)


def ensureLogin(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if 'username' not in login_session:
            flash("You need to login to complete this action")
            return redirect(url_for('showLogin'))
        return func(*args, **kwargs)
    return decorated_function

# For more details on oauth2 flow with google, visit https://developers.google.com/identity/protocols/OAuth2WebServer
# The implementation below is slightly different
# The ajax portion in the login will call this function
@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    # First check if the state_token of the server when the user clicked login is same as the state_token
    # when the user POSTs. Otherwise, it may be a malicious attack on the server
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps("Invalid state token"), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    print("Verified state token, so it is the same user")
    # The code here is the data sent in the ajax call to this server. It was received from google when the user
    # approved the request
    code = request.data

    try:
        # convert the authorization code into a credential object by talking to the token_uri from client_secrets
        # this object will contain the access token and the refresh token
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
        print("Converted auth code to credentials object by talking to the token uri in client secrets")
    except FlowExchangeError:
        response = make_response(json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Validate access token in the credentials object
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={}'.format(access_token))
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    print("Used access token from credentials object to obtain token info from the google apis")
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify the access token is used for the right user
    # The sub here is REQUIRED. Subject Identifier. A locally unique and
    # never reassigned identifier within the Issuer for the End-User, which is intended to be consumed by the Client
    # This should be same as the user_id in the result object obtained by querying tokeninfo on googleapis
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(json.dumps("Token's user id does not match given user id"), 401)
        response.headers['Content-Type'] = 'application/json'
        return  response
    print("id token in the credentials object matches the user id in the tokeninfo")

    # Verify the access token is valid for the web server
    if result['issued_to'] != CLIENT_ID:
        response = make_response(json.dumps("Token's client ID does not match the app"), 401)
        response.headers['Content-Type'] = 'application/json'
        return  response
    print("tokeninfo's client id matches the app's client id")

    # Check to see if a user is already logged in
    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and stored_gplus_id == gplus_id:
        response = make_response(json.dumps("Current user already connected"), 200)
        response.headers['Content-Type'] = 'application/json'
        return  response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials
    login_session['gplus_id'] = gplus_id

    # Get user info by passing in the access token
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['access_token'] = access_token
    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    login_session['user_id'] = getUserID(login_session['email'])

    if login_session['user_id'] is None:
        createUser(login_session)

    print(login_session['user_id'])
    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as {}".format(login_session['username']))
    print("done!")
    return output


@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session.get('access_token')
    print('In gdisconnect access token is {}'.format(access_token))
    print('User name is: ')
    print(login_session['username'])
    if access_token is None:
        print('Access Token is None')
        response = make_response(json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token={}'.format(login_session['access_token'])
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print('result is ')
    print(result)
    if result['status'] == '200':
        del(login_session['access_token'])
        del(login_session['gplus_id'])
        del(login_session['username'])
        del(login_session['email'])
        del(login_session['picture'])
        del(login_session['user_id'])
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


@app.route('/restaurants/<int:restaurant_id>/menu/JSON')
def restaurantMenuJSON(restaurant_id):
    items = session.query(MenuItem).filter_by(restaurant_id=restaurant_id).all()
    return jsonify(MenuItems=[i.serialize for i in items])


@app.route('/restaurants/<int:restaurant_id>/menu/<int:menu_id>/JSON')
def menuItemJSON(restaurant_id, menu_id):
    item = session.query(MenuItem).filter_by(restaurant_id=restaurant_id, id=menu_id).one()
    return jsonify(MenuItem=item.serialize)


@app.route('/restaurants/JSON')
def restaurantsJSON():
    restaurants = session.query(Restaurant).all()
    return jsonify(Restaurants=[r.serialize for r in restaurants])


@app.route('/')
@app.route('/restaurants/')
def showRestaurants():
    restaurants = session.query(Restaurant).all()
    return render_template('restaurant.html', restaurants=restaurants)


@app.route('/restaurant/new', methods=['GET', 'POST'])
@ensureLogin
def newRestaurant():
    if request.method == 'POST':
        new_restaurant = Restaurant(name=request.form['name'], user_id=getUserID(login_session['email']))
        session.add(new_restaurant)
        session.commit()
        flash("New restaurant " + new_restaurant.name + " added!")
        return redirect(url_for('showRestaurants'))
    else:
        return render_template('newRestaurant.html')


@app.route('/restaurants/<int:restaurant_id>/edit', methods=['GET', 'POST'])
@ensureLogin
def editRestaurant(restaurant_id):
    editedRestaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    if request.method == 'POST':
        # return "Restaurant needs to be edited and a flash message displayed, redirect to restaurants page"
        if request.form['name']:
            editedRestaurant.name = request.form['name']
        session.commit()
        flash("Restaurant " + editedRestaurant.name + " edited!")
        return redirect(url_for('showRestaurants'))
    else:
        return render_template('editRestaurant.html', restaurant_id=restaurant_id, restaurant=editedRestaurant)


@app.route('/restaurants/<int:restaurant_id>/delete', methods=['GET', 'POST'])
@ensureLogin
def deleteRestaurant(restaurant_id):
    deletedRestaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    if request.method == 'POST':
        session.delete(deletedRestaurant)
        flash("Restaurant " + deletedRestaurant.name + " deleted!")
        return redirect(url_for('showRestaurants'))
    else:
        return render_template('deleteRestaurant.html', restaurant_id=restaurant_id, restaurant=deletedRestaurant)


@app.route('/')
@app.route('/restaurants/<int:restaurant_id>/')
def restaurantMenu(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    menu_items = session.query(MenuItem).filter_by(restaurant_id=restaurant.id)
    return render_template("menu.html", restaurant=restaurant, items=menu_items)


@app.route('/restaurants/<int:restaurant_id>/menuitems/new', methods=['GET', 'POST'])
@ensureLogin
def newMenuItem(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    if request.method == 'POST':
        newItem = MenuItem(name=request.form['name'], description=request.form['description'],
                           price=request.form['price'], course=request.form['course'], restaurant_id=restaurant_id,
                           user_id=restaurant.user_id)
        session.add(newItem)
        session.commit()
        flash("New menu Item " + newItem.name + " created!")
        return redirect(url_for('restaurantMenu', restaurant_id=restaurant_id))
    else:
        return render_template('newmenuitem.html', restaurant_id=restaurant_id)


@app.route('/restaurants/<int:restaurant_id>/menuitems/<int:menu_id>/edit', methods=['GET', 'POST'])
@ensureLogin
def editMenuItem(restaurant_id, menu_id):
    editedItem = session.query(MenuItem).filter_by(id=menu_id).one()
    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
        if request.form['price']:
            editedItem.price = request.form['price']
        if request.form['course']:
            editedItem.course = request.form['course']
        session.commit()
        flash("Menu item " + editedItem.name + " edited!")
        return redirect(url_for('restaurantMenu', restaurant_id=restaurant_id))
    else:
        # USE THE RENDER_TEMPLATE FUNCTION BELOW TO SEE THE VARIABLES YOU SHOULD USE IN YOUR EDITMENUITEM TEMPLATE
        return render_template('editmenuitem.html', restaurant_id=restaurant_id, menu_id=menu_id,
                               item=editedItem)


@app.route('/restaurants/<int:restaurant_id>/menuitems/<int:menu_id>/delete', methods=['GET', 'POST'])
@ensureLogin
def deleteMenuItem(restaurant_id, menu_id):
    deleteItem = session.query(MenuItem).filter_by(id=menu_id).one()
    if request.method == 'POST':
        session.delete(deleteItem)
        session.commit()
        flash("Menu item " + deleteItem.name + " deleted!")
        return redirect(url_for('restaurantMenu', restaurant_id=restaurant_id))
    else:
        return render_template('deleteMenuItem.html', item=deleteItem)


if __name__ == '__main__':
    app.secret_key = 'some_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)