from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    return json.loads(json_util.dumps(data))

######################################################################
# INSERT CODE HERE
######################################################################
@app.route("/health")
def health():
    return jsonify({"status": "OK"}), 200

@app.route("/count")
def count():
    if songs_list:
        return jsonify(count=len(songs_list)), 200
    return jsonify({"message": "Internal server error"}), 500



@app.route("/song", methods=["GET"])
def songs():
    all_songs = list(db.songs.find({}))  # Fetch and convert cursor to list
    for song in all_songs:
        # Format _id as nested dictionary with "$oid" key
        song["_id"] = {"$oid": str(song["_id"])}
    return jsonify({"songs": all_songs}), 200


@app.route("/song", methods=["POST"])
def create_song():
    song_data = request.json 
    inserted_id = str(ObjectId())

    song = next((item for item in songs_list if int(item['id']) == int(song_data['id'])), None)

    if not song:
        song_data['_id'] = {"$oid": inserted_id}
        songs_list.append(song_data)
        
        response = {
            "inserted id": {
                "$oid": inserted_id
            }
        }
        return jsonify(response), 201
    else:
        return jsonify({
            "message": f"Song with {song_data['id']} already present."
        }), 302


@app.route("/song/<int:id>", methods=["PUT"])
def update_song(id):
    song_data = request.json
    existing_song = next((song for song in songs_list if int(song['id']) == id), None)
    
    if existing_song:
        update_result = db.songs.update_one(
            {'id': existing_song['id']},
            {'$set': {
                'title': song_data.get("title", existing_song["title"]),
                'lyrics': song_data.get("lyrics", existing_song["lyrics"])
            }}
        )

        if update_result.modified_count == 0:
            return jsonify({"message": "song found but nothing updated"}), 200

        updated_song = db.songs.find_one({'id': existing_song['id']})
        
        if updated_song:
            response_data = {
                "_id": {"$oid": str(updated_song["_id"])},
                "id": updated_song["id"],
                "lyrics": updated_song["lyrics"],
                "title": updated_song["title"]
            }
            return jsonify(response_data), 201
        else:
            return jsonify({"message": "updated song not found"}), 404
    else:
        return jsonify({"message": "song not found"}), 404

@app.route("/song/<int:id>", methods=["DELETE"])
def delete_song(id):
    # Find the song by `id` in the songs list
    find_song = next((song for song in songs_list if int(song['id']) == id), None)
    
    if find_song:
        # Delete the song from the database using the custom `id` field
        delete_result = db.songs.delete_one({'id': find_song['id']})
        
        # Check if a document was actually deleted
        if delete_result.deleted_count > 0:
            return '',204
        else:
            return jsonify({"message": "song not found"}), 404
    else:
        return jsonify({"message": "song not found"}), 404









