from flask import Flask, render_template, request, redirect, jsonify, url_for, flash
app = Flask(__name__)

from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker, scoped_session
from database_setup import Genre, Movies, Editor, Base

#Oauth imports
from flask import session as login_session
import random, string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

CLIENT_ID = json.loads(open('client_secrets.json', 'r').read())['web']['client_id']

#Connect to database and create the session
engine = create_engine('postgresql://catalog:password@localhost/moviegenre')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = scoped_session(DBSession)

#Create token and store in login session
@app.route('/login')
def showLogin():
  state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(32))
  login_session['state'] = state
  return render_template('login.html', state=state)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    if request.args.get('state') != login_session['state']:
        return jsonify('Invalid state parameter'), 401
    #Obtain authorization code
    code = request.data

    try:
        #Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        return jsonify('Failed to upgrade the authorization code.'), 401

    #Check access token validity
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' %
           access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1].decode('utf-8'))

    #If there was an error in the access token info, abort.
    if result.get('error') is not None:
        return jsonify(result.get('error')), 500

    #Verify that the access token is used for the intended user.
    google_id = credentials.id_token['sub']
    if result['user_id'] != google_id:
        return jsonify("Token's user ID doesn't match given user ID."), 401

    #Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        return jsonify("Token's client ID doesn't match app's."), 401

    #Check to see if user is already logged in
    stored_credentials = login_session.get('access_token')
    stored_google_id = login_session.get('google_id')

    if stored_credentials is not None and google_id == stored_google_id:
        return jsonify('Current user is already connected.'), 200

    #Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['google_id'] = google_id

    #Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)
    print('the answer is: %s' % answer)
    data = answer.json()
    print('the data is: %s' % data)

    
    login_session['username'] = data.get('name', 'friend')
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += '" style="width: 150px; height: 150px; border-radius: 150px; -webkit-border-radius: 150px; -moz=border-radius: 150px;">'
    flash("You are now logged in as %s" % login_session['username'])
    print("Done!")
    return output

# Create a new user.
def createUser(login_session):
    newUser = Editor(name=login_session['username'],
                   email=login_session['email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(Editor).filter_by(email=login_session['email']).one()
    return user.id

# Get new users info.
def getUserInfo(user_id):
    user = session.query(Editor).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(Editor).filter_by(email=email).one()
        return user.id
    except:
        return None

@app.route('/gdisconnect')
def gdisconnect():
  access_token = login_session.get('access_token')
  if access_token is None:
    return jsonify('Current user is not logged in.'), 401

  url = ('https://accounts.google.com/o/oauth2/revoke?token=%s' % login_session['access_token'])
  h = httplib2.Http()
  result = h.request(url, 'GET')[0]

  if result['status'] == '200':
    del login_session['access_token']
    del login_session['google_id']
    del login_session['username']
    del login_session['email']
    del login_session['picture']
    return jsonify('Successfully logged out.'), 200
  else:
    return jsonify('Failed to revoke user token'), 400

#JSON api routes
#List all the movies in specified genre
@app.route('/genres/<genre_type>/movies/JSON')
def genreListJSON(genre_type):
  genre = session.query(Genre).filter_by(type = genre_type).one()
  movies = session.query(Movies).filter_by(type = genre_type).all()
  return jsonify(MovieList = [m.serialize for m in movies])

#Show the JSON for a specified movie
@app.route('/genres/<genre_type>/movies/<int:movie_id>/JSON')
def movieJSON(genre_type, movie_id):
  movie = session.query(Movies).filter_by(id = movie_id).one()
  return jsonify(movie = movie.serialize)

#Homepage (Shows all genres)
@app.route('/')
@app.route('/genres')
def showGenres():
  genres = session.query(Genre).order_by(asc(Genre.type))
  if 'username' not in login_session:
    return render_template('genres.html', genres=genres)
  else:
    return render_template('logoutgenres.html', genres=genres)

#Show movies in picked genre
@app.route('/genres/<genre_type>/')
@app.route('/genres/<genre_type>/movies/')
def showMovies(genre_type):
  genre = session.query(Genre).filter_by(type = genre_type).one()
  contributor = getUserInfo(login_session['user_id'])
  movies = session.query(Movies).filter_by(genre_id = genre.id).all()
  if 'username' not in login_session:
    return render_template('publicMovies.html', genre = genre, movies = movies, contributor = contributor)
  elif 'username' in login_session and contributor.id == login_session['user_id']:
    return render_template('movies.html', genre=genre, movies=movies, contributor=contributor)
  else:
    return render_template('addMovie.html', genre = genre, movies = movies, contributor = contributor)

#Add new movie to a genre category
@app.route('/genres/<genre_type>/movies/new/', methods=['GET', 'POST'])
def newMovie(genre_type):
  if 'username' not in login_session:
    return redirect('/login')
  if request.method == 'POST':
    genre = session.query(Genre).filter_by(type = genre_type).one()
    user_id = getUserInfo(login_session['user_id'])
    newMovie = Movies(title = request.form['title'], year = request.form['year'], plot = request.form['plot'], poster = request.form['poster'], type = genre_type, user_id = user_id.id)
    session.add(newMovie)
    session.commit()
    flash('%s was added to the list successfully' % newMovie.title)
    return redirect(url_for('showMovies', genre_type = genre_type))
  else:
    return render_template('newMovie.html', genre_type = genre_type)

#Edit movie information
@app.route('/genres/<genre_type>/movies/<int:movie_id>/edit/', methods=['GET', 'POST'])
def editMovie(genre_type, movie_id):
  editedMovie = session.query(Movies).filter_by(id = movie_id).one()
  genre = session.query(Genre).filter_by(type = genre_type).one()
  if 'username' not in login_session:
    return redirect('/login')
  if editedMovie.user_id != login_session['user_id']:
    return "<script>function alert() {alert('You are not Authorized to edit this movie.');}</script><body onload='alert()'>"
  if request.method == 'POST':
    if request.form['title']:
      editedMovie.title = request.form['title']
    if request.form['year']:
      editedMovie.year = request.form['year']
    if request.form['plot']:
      editedMovie.plot = request.form['plot']
    session.add(editedMovie)
    session.commit()
    flash('Movie has been updated.')
    return redirect(url_for('showMovies', genre_type = genre_type))
  else:
    return render_template('editMovie.html', edit=editedMovie, genre=genre)

#Delete movie from database
@app.route('/genres/<genre_type>/movies/<int:movie_id>/delete/', methods=['GET', 'POST'])
def deleteMovie(genre_type, movie_id):
  genre = session.query(Genre).filter_by(type=genre_type).one()
  movieToDelete = session.query(Movies).filter_by(id = movie_id).one()
  if 'username' not in login_session:
    return redirect('/login')
  if movieToDelete.user_id != login_session['user_id']:
    return "<script>function alert() {alert('You are not Authorized to delete this movie.');}</script><body onload='alert()'>"
  if request.method == 'POST':
    session.delete(movieToDelete)
    session.commit()
    flash('Movie successfully deleted.')
    return redirect(url_for('showMovies', genre_type = genre_type))
  else:
    return render_template('deleteMovie.html', delete = movieToDelete, genre=genre)

  



if __name__ == '__main__':
  app.debug = False
  app.run()
