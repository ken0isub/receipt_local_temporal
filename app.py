import cv2
from flask import Flask, request, redirect, render_template, flash, session, url_for
from google.cloud import vision
import io
import numpy as np
import os
import re
# from tensorflow.keras.models import Sequential, load_model
# from tensorflow.keras.preprocessing import image
from werkzeug.utils import secure_filename
from receipt_prediction import allowed_file, predict_receipt
from read_receipts import read_costco, read_seven, read_lawson, read_kasumi
import gspread
import datetime
from oauth2client.service_account import ServiceAccountCredentials
from to_sheet import write_sheet

UPLOAD_FOLDER = "./static/uploads"
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = 'del/aid-temp.json'
client = vision.ImageAnnotatorClient()


def allowed_file(filename, ALLOWED_EXTENSIONS):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)
        if file and allowed_file(file.filename, ALLOWED_EXTENSIONS):
            filename = secure_filename(file.filename)
            file.save(os.path.join(UPLOAD_FOLDER, filename))

            return redirect(url_for('page2', filename=filename))

    return render_template("index.html")


@app.route('/page2/<filename>', methods=['GET', 'POST'])
def page2(filename):
    if request.method == 'POST':
        store = request.form.get('store')
        price = request.form.get('price')
        date = request.form.get('date')
        category = request.form.get('category')
        point = request.form.get('point')
        who = request.form.get('who')
        note = request.form.get('note')

        write_sheet(price, store, category, date, note, who, point)
        return 'POSTED'

    UPLOAD_FOLDER = "./static/uploads"
    UPLOAD_FOLDER2 = "../static/uploads"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    filepath2 = os.path.join(UPLOAD_FOLDER2, filename)
    pred_store = 'failed'
    price = 'failed'
    date_dt = 'failed'

    pred_store = predict_receipt(filepath, 'models/ML')
    print(pred_store)

    #get result from google vision API
    with io.open(filepath, 'rb') as image_file:
        content = image_file.read()
    image_2 = vision.Image(content=content)
    response = client.document_text_detection(image=image_2)

    discount = ''
    if pred_store == 'costco':
        price, date_dt = read_costco(response)
    else:
        pass
    if pred_store == 'seven':
        price, date_dt = read_seven(response)
    if pred_store == 'lawson':
        price, date_dt = read_lawson(response)
    if pred_store == 'familymart':
        price, date_dt = read_lawson(response)
    if pred_store == 'kasumi':
        price, date_dt, discount = read_kasumi(response)

    print(price)

    return render_template('page2.html', filepath=filepath2, price=price, store=pred_store,
                           date=date_dt, discount=discount)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)