from flask import Flask, jsonify
from flask_restful import Api
import logging
import subprocess

logging.basicConfig(level='DEBUG', format="%(asctime)s - %(name)-18s - %(levelname)-7s - %(message)s")

logger = logging.getLogger(__name__)
app = Flask(__name__)
api = Api(app)


@app.route('/restart')
def restart():
    logger.info("Restarting Dino by api request")

    try:
        output = subprocess.run(
            ['/usr/local/bin/dino-hup-restart-with-cache-warmup.sh'],
            capture_output=True,
        )
        logger.info(output.stdout)
        logger.info(output.stderr)
    except Exception as e:
        logger.error(e)
        logger.exception(e)
        return jsonify({'status': 'error', 'message': str(e)})

    return jsonify({'status': 'ok'})
