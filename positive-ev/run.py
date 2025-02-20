from app import create_app
from app.config import BaseConfig

app = create_app(BaseConfig)

if __name__ == '__main__':
    app.run(debug=True, port=5001, host='0.0.0.0') 