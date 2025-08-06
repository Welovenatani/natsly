from flask_compress import Compress

def init_compression(app):
    Compress(app)
    app.config['COMPRESS_REGISTER'] = True
    app.config['COMPRESS_MIMETYPES'] = [
        'text/html', 'text/css', 'text/xml',
        'application/json', 'application/javascript',
        'image/svg+xml'
    ]
