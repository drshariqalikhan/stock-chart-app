import os
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder='static')
CORS(app)

# Basic Test API
@app.route('/api/test')
def test_api():
    return jsonify({
        "status": "success",
        "message": "Flask backend is running on Render!"
    })

# Serve Frontend
@app.route('/')
def serve_index():
    return send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

if __name__ == '__main__':
    # Render uses the PORT environment variable
    port = int(os.environ.get("PORT", 3000))
    app.run(host='0.0.0.0', port=port)