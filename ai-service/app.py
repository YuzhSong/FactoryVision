from flask import Flask, jsonify

from config import Config


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    @app.get("/health")
    def health_check():
        return jsonify(
            {
                "service": app.config["SERVICE_NAME"],
                "status": "ok",
                "stage": "skeleton",
            }
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
