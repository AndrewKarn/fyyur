import os
SECRET_KEY = os.urandom(32)
# Grabs the folder where the script runs.
basedir = os.path.abspath(os.path.dirname(__file__))

# Enable debug mode.
DEBUG = True

# Connect to the database

SQLALCHEMY_DATABASE_URI = 'postgres://sozukvyiradwfz:807483e334f9ce8e0b9c1de753539a04b1d6ece79ffd82d306cbc54ea936706e@ec2-54-86-57-171.compute-1.amazonaws.com:5432/d1pae93kccdp8j'
SQLALCHEMY_TRACK_MODIFICATIONS = True
TEMPLATES_AUTO_RELOAD=True