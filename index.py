from flask import Flask

app = Flask(__name__)


@app.route('/')
def index():
    return "Welcome to Free AI Page"


def route_photo():
    return "This is A Photo App."


app.add_url_rule('/photo', 'route_photo', route_photo)


if __name__ == "__main__":
    app.run(debug=True)
