#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
import sys
from logging import Formatter, FileHandler
from flask_wtf import Form
from flask_migrate import Migrate
from sqlalchemy import event
from sqlalchemy.event import listen, listens_for
from forms import *

#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)

migrate = Migrate(app, db)
#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#


class Venue(db.Model):
    __tablename__ = 'venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean, unique=False, default=True)
    seeking_description = db.Column(db.String(120))
    genres = db.Column(db.ARRAY(db.String(120)))
    website = db.Column(db.String(120))


class Artist(db.Model):
    __tablename__ = 'artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    genres = db.Column(db.ARRAY(db.String(120)))
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean)
    seeking_description = db.Column(db.String(500))
    website = db.Column(db.String(120))


class Show(db.Model):
    __tablename__ = 'show'
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime)
    venue_id = db.Column(db.Integer, db.ForeignKey('venue.id'), nullable=False)
    venue_name = db.relationship('Venue', backref=db.backref('shows'))
    artist_id = db.Column(db.Integer, db.ForeignKey(
        'artist.id'), nullable=False)
    artist = db.relationship('Artist', backref=db.backref('shows'))


def format_datetime(value, format='medium'):
    date = dateutil.parser.parse(value)
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format)


app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#


@app.route('/')
def index():
    return render_template('pages/home.html')


#  Venues get Venues (Read)
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
    venues = db.session.query(Venue).all()
    data = []
    result = dict()
    for venue in venues:
        key_name = venue.city + venue.state
        if not key_name in result:
            result[key_name] = {
                'state': venue.state,
                'city': venue.city,
                'venues': []
            }
        result[key_name]['venues'].append(venue)

    for k, v in result.items():
        data.append(v)

    return render_template('pages/venues.html', areas=data)


@app.route('/venues/search', methods=['POST'])
def search_venues():
    search_term = request.form.get('search_term', '')
    venues = Venue.query.filter(Venue.name.ilike(f'%{search_term}%')).all()
    count = 0
    for v in venues:
        v = v.id
        count += 1

    record = {
        'count': count,
        'data': venues
    }
    return render_template('pages/search_venues.html', results=record, search_term=search_term)

# Helper lib


#  ----------------------------------------------------------------
# Takes in an iterator and returns a keyed dict based on primary key, I learned this pattern from my coworker when we worked on a php app.
def arrayToHash(data):
    result = dict()
    for ele in data:
        result[(ele.id)] = ele
    return result

# takes in a data model type and will sort throught the upcoming and past shows
# returns a dictionary of all shows for the passed in Venue or Artist
# Input: 
# modelType  STR must be either 'venue' or 'artist
# entity_id int must be the id for the specfic venue or artist
# entiy_data sqlalchemy data object, pass the whole thing in for gr8 results
def getUpcomingAndPastShows(modelType, entity_id, entiy_data):
    past_shows = []
    upcoming_shows = []
    if (modelType == 'venue'):
        data = db.session.query(Show).filter(Show.venue_id == entity_id).all()
    else:
        data = db.session.query(Show).filter(Show.artist_id == entity_id).all()
    for d in data:
        # building row based on the entity that's requested
        if (modelType == 'venue'):
            artist = db.session.query(Artist).filter(Artist.id == d.artist_id)
            row = {
                "artist_id": d.artist_id,
                "artist_name": artist.name,
                "artist_image_link": artist.image_link,
                "start_time": d.start_time.strftime('%m/%d/%Y')
            }
        else:
            venue = db.session.query(Venue).filter(Venue.id == d.venue_id)
            row = {
                "venue_id": d.venue_id,
                "venue_name": venue.name,
                "venue_image_link": venue.image_link,
                "start_time": d.start_time.strftime('%m/%d/%Y')
            }
        if (d.start_time < datetime.now()):
            past_shows.append(row)
        else:
            upcoming_shows.append(row)
    result = {
        'past_shows': past_shows,
        'upcoming_shows': upcoming_shows
    }
    return result


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    venue = Venue.query.get(venue_id)
    shows_info = getUpcomingAndPastShows('venue', venue_id, venue)
    data = {
        "id": venue.id,
        "name": venue.name,
        "genres": venue.genres,
        "address": venue.address,
        "city": venue.city,
        "state": venue.state,
        "phone": venue.phone,
        "website": venue.website,
        "facebook_link": venue.facebook_link,
        "seeking_talent": venue.seeking_talent,
        "seeking_description": venue.seeking_description,
        "image_link": venue.image_link,
        "past_shows": shows_info['past_shows'],
        "upcoming_shows": shows_info['upcoming_shows'],
        "past_shows_count": len(shows_info['past_shows']),
        "upcoming_shows_count": len(shows_info['upcoming_shows']),
    }
    return render_template('pages/show_venue.html', venue=data)

#  Venues Create
#  ----------------------------------------------------------------


@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    error = False
    data = request.form
    vname = data['name']
    vcity = data['city']
    vstate = data['state']
    vaddress = data['address']
    vphone = data['phone']
    vgenres = data['genres']
    vfb_link = data['facebook_link']
    vimage_link = data['image_link']
    try:
        db.session.add(Venue(
            city=vcity,
            state=vstate,
            name=vname,
            address=vaddress,
            phone=vphone,
            facebook_link=vfb_link,
            genres=vgenres,
            seeking_talent=False,
            website="",
            image_link=vimage_link
        ))
    except expression:
        error = true
    finally:
        if not error:
            db.session.commit()
            flash('Venue ' + request.form['name'] +
                  ' was successfully listed!')
        else:
            flash('An error occurred. Venue ' +
                  vname + ' could not be listed.')
            db.session.rollback()
    return render_template('pages/home.html')

#  Delete Venues
#  ----------------------------------------------------------------


@app.route('/venues/<venue_id>', methods=['POST'])
def delete_venue(venue_id):
    # N.B becuase of how i set up Show db i need to clear any shows associated with this artist before I can delete them
    try:
        db.session.query(Show).filter(Show.venue_id == venue_id).delete()
        db.session.query(Venue).filter(Venue.id == venue_id).delete()
        db.session.commit()
        flash('Venue was successfully deleted!')
    except:
        print(sys.exc_info())
        flash('An error occurred. Venue could not be deleted.')
    finally:
        db.session.close()
    return redirect(url_for('venues'))


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    form = VenueForm()
    venue = Venue.query.get(venue_id)
    # If we got anything back the if statement will catch it and we'll do the block of code to fill the form.
    if venue:
        form.name.data = venue.name
        form.city.data = venue.city
        form.state.data = venue.state
        form.phone.data = venue.phone
        form.genres.data = venue.genres
        form.facebook_link.data = venue.facebook_link
        form.image_link.data = venue.image_link
        form.website.data = venue.website
        form.seeking_talent.data = venue.seeking_talent
        form.seeking_description.data = venue.seeking_description
        form.address.data = venue.address
    return render_template('forms/edit_venue.html', form=form, venue=venue)

# Edit venues


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    if (request.form):
        error = False
        venue = Venue.query.get(venue_id)
        try:
            venue.name = request.form['name']
            venue.city = request.form['city']
            venue.state = request.form['state']
            venue.phone = request.form['phone']
            venue.genres = request.form.getlist('genres')
            venue.image_link = request.form['image_link']
            venue.seeking_description = request.form['seeking_description']
            venue.facebook_link = request.form['facebook_link']
            venue.website = request.form['website']
            venue.address = request.form['address']
            venue.seeking_talent = ('seeking_talent' in request.form)
            db.session.commit()
        except:
            error = True
            db.session.rollback()
            print(sys.exc_info())
        finally:
            db.session.close()
        if error:
            flash('An error occurred. Venue could not be changed.')
        if not error:
            flash('Venue was successfully updated!')
        return redirect(url_for('show_venue', venue_id=venue_id))
    else:
        return redirect(url_for('show_venue', venue_id=venue_id))

#  Artists
#  ----------------------------------------------------------------
# get Venues
# ----------------------------------------------------------------
@app.route('/artists')
def artists():
    result = db.session.query(Artist.id, Artist.name).all()
    return render_template('pages/artists.html', artists=result)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    search_term = request.form.get('search_term', '')
    artists = Artist.query.filter(Artist.name.ilike(f'%{search_term}%')).all()
    count = 0
    for a in artists:
        a = a.id
        count += 1

    response = {
        'count': count,
        'data': artists
    }
    return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    artist = db.session.query(Artist).filter(Artist.id == artist_id).one()

    show_info = getUpcomingAndPastShows('artist', artist_id, artist)
    data = {
        "id": artist.id,
        "name": artist.name,
        "genres": artist.genres,
        "city": artist.city,
        "state": artist.state,
        "phone": artist.phone,
        "website": artist.website,
        "facebook_link": artist.facebook_link,
        "seeking_venue": artist.seeking_venue,
        "seeking_description": artist.seeking_description,
        "image_link": (artist.image_link),
        "past_shows": show_info['past_shows'],
        "upcoming_shows": show_info['upcoming_shows'],
        "past_shows_count": len(show_info['past_shows']),
        "upcoming_shows_count": len(show_info['upcoming_shows']),
    }

    return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    form = ArtistForm()
    artist = Artist.query.get(artist_id)

    if artist:
        form.name.data = artist.name
        form.city.data = artist.city
        form.state.data = artist.state
        form.phone.data = artist.phone
        form.genres.data = artist.genres
        form.facebook_link.data = artist.facebook_link
        form.image_link.data = artist.image_link
        form.website.data = artist.website
        form.seeking_venue.data = artist.seeking_venue
        form.seeking_description.data = artist.seeking_description

    return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    if (request.form):
        error = False
        artist = Artist.query.get(artist_id)

        try:
            artist.name = request.form['name']
            artist.city = request.form['city']
            artist.state = request.form['state']
            artist.phone = request.form['phone']
            artist.genres = request.form.getlist('genres')
            artist.image_link = request.form['image_link']
            artist.facebook_link = request.form['facebook_link']
            artist.website = request.form['website']
            artist.seeking_venue = ('seeking_venue' in request.form)
            artist.seeking_description = request.form['seeking_description']

            db.session.commit()
        except:
            error = True
            db.session.rollback()
            print(sys.exc_info())
        finally:
            db.session.close()
        if error:
            flash('An error occurred. Artist could not be changed.')
        if not error:
            flash('Artist was successfully updated!')
        return redirect(url_for('show_artist', artist_id=artist_id))
    else:
        return redirect(url_for('show_artist', artist_id=artist_id))


#  Create Artist / PUT
#  ----------------------------------------------------------------


@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    has_error = False
    try:
        name = request.form['name']
        city = request.form['city']
        state = request.form['state']
        phone = request.form['phone']
        genres = request.form.getlist('genres'),
        facebook_link = request.form['facebook_link']
        image_link = request.form['image_link']
        website = request.form['website']
        seeking_venue = ('seeking_venue' in request.form)
        seeking_description = request.form['seeking_description']

        artist = Artist(
            name=name,
            city=city,
            state=state,
            phone=phone,
            genres=genres,
            facebook_link=facebook_link,
            image_link=image_link,
            website=website,
            seeking_venue=seeking_venue,
            seeking_description=seeking_description)
        db.session.add(artist)
        db.session.commit()
    except:
        has_error = True
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()
    if has_error:
        flash('An error occurred. Artist ' +
              request.form['name'] + ' could not be listed.')
    if not has_error:
        flash('Artist ' + request.form['name'] + ' was successfully listed!')
    return render_template('pages/home.html')



#  Shows, only one controller method is delete rest are all get related
# If we had a lot of data in the db, a db call to get artist and venue info in each iteration would be overkill, so I did most of the manipulation in on the python side with just a single db call per entity.
@app.route('/shows')
def shows():
    data = []
    shows = Show.query.all()
    artists = arrayToHash(Artist.query.all())
    venues = arrayToHash(Venue.query.all())
    for show in shows:
        this_venue_id = show.venue_id
        this_artist_id = show.artist_id
        data.append({
            "venue_id": this_venue_id,
            "venue_name": venues[this_venue_id].name,
            "artist_id": this_artist_id,
            "artist_name": artists[this_artist_id].name,
            "artist_image_link": artists[this_artist_id].image_link,
            "start_time": str(show.start_time)
        })
    print(data)
    return render_template('pages/shows.html', shows=data)


@app.route('/shows/create')
def create_shows():
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    error = False
    try:
        artist_id = request.form['artist_id']
        venue_id = request.form['venue_id']
        start_time = request.form['start_time']

        show = Show(artist_id=artist_id, venue_id=venue_id,
                    start_time=start_time)
        db.session.add(show)
        db.session.commit()
    except:
        error = True
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()
    if error:
        flash('An error occurred. Show could not be listed.')
    if not error:
        flash('Show was successfully listed')
    return render_template('pages/home.html')

# For deleteing shows, I figured there is no need to edit shows since it is just a pair of 2 ids and it's easy to make that new record and now delete the old.
@app.route('/shows/delete/<show_id>', methods=['POST'])
def delete_show(show_id):
    try:
        Show.query.get(show_id).delete()
        db.session.commit()
        flash('Show was successfully deleted!')
    except:
        print(sys.exc_info())
        flash('An error occurred. Show could not be deleted.')
    finally:
        db.session.close()
    return redirect(url_for('shows'))


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#
# Default port:
if __name__ == '__main__':
    app.jinja_env.auto_reload = True
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
