import os
from flask import Flask, render_template, request, redirect, send_file
import boto3
from werkzeug.utils import secure_filename
import logging
import textract
import tabula
from trp import Document

import tesserocr
from PIL import Image

import PyPDF2
import json

app = Flask(__name__, template_folder='template')
UPLOAD_FOLDER = "/uploads"
BUCKET = "celebs-reck-s3"
SUCCESS = None


@app.route('/')
def entry_point():
    return render_template('index.html')


@app.route("/storage")
def storage():
    contents = list_files("celebs-reck-s3")
    return render_template('storage.html', contents=contents)


@app.route("/upload", methods=['POST'])
def upload():
    if request.method == "POST":
        f = request.files['file']
        if f:
            filename = secure_filename(f.filename)
            f.save(filename)
            s3_client = boto3.client('s3')
            response = s3_client.upload_file(
                Filename=filename, Bucket=BUCKET, Key=filename)
            app.logger.info(response)
            # upload_file(f"/uploads/{f.filename}", BUCKET)
            # print("Response", response)
            # app.logger.info(type(response))
    return redirect("/success")


@app.route('/success')
def upload_success():
    contents = list_files("celebs-reck-s3")
    textract = boto3.client('textract')
    comprehend = boto3.client('comprehend')

    total = []

    for doc in contents:
        documentName = doc['Key']
        fileType = documentName.split(".")

        if fileType[1] == 'png':
            response = textract.detect_document_text(
                Document={
                    'S3Object': {
                        'Bucket': BUCKET,
                        'Name': documentName
                    }
                })
            text = ""
            for item in response["Blocks"]:
                if item["BlockType"] == "LINE":
                    text = text + " " + item["Text"]

            # Detect sentiment
            sentiment = comprehend.detect_syntax(LanguageCode="en", Text=text)
            synTokArr = sentiment.get('SyntaxTokens')

            for i in synTokArr:
                obj = {}
                if i['Text'] == "MMR":
                    obj['name'] = documentName.split(".")[0]
                    obj['class'] = 'MMR REPORT'
                    total.append(obj)
                elif i['Text'] == "Flu":
                    obj['name'] = documentName.split(".")[0]
                    obj['class'] = 'Flu REPORT'
                    total.append(obj)

        if fileType[1] == 'JPG':
            obj = detect_faces(documentName)
            total.append(obj)

    return render_template('success.html', total=total)


@app.route('/success2')
def upload_success2():
    contents = list_files("celebs-reck-s3")
    return render_template('success.html', contents=contents)


@app.route('/ocr')
def ocr():
    pdfFileObj = open('table.pdf', 'rb')
    pdfReader = PyPDF2.PdfFileReader(pdfFileObj)
    pageObj = pdfReader.getPage(0)
    text = pageObj.extractText()
    return text


@app.route('/comp')
def comp():
    # Amazon Textract client
    textract = boto3.client('textract')
    documentName = "Screen_Shot_2020-11-03_at_9.28.51_PM.png"
    response = textract.detect_document_text(
        Document={
            'S3Object': {
                'Bucket': BUCKET,
                'Name': documentName
            }
        })
    text = ""
    for item in response["Blocks"]:
        if item["BlockType"] == "LINE":
            print('\033[94m' + item["Text"] + '\033[0m')
            text = text + " " + item["Text"]

    # Amazon Comprehend client
    comprehend = boto3.client('comprehend')
    # Detect sentiment
    sentiment = comprehend.detect_syntax(LanguageCode="en", Text=text)
    #print ("\nSentiment\n========\n{}".format(sentiment.get('Sentiment')))
    synTokArr = sentiment.get('SyntaxTokens')

    return render_template('table.html', contents=synTokArr)


@app.route('/profile')
def detect_faces(picture):
    # Amazon Textract client
    rekognition = boto3.client('rekognition')

    obj = {}

    response = rekognition.detect_faces(
        Image={'S3Object': {'Bucket': BUCKET, 'Name': picture}}, Attributes=['ALL'])

    for faceDetail in response['FaceDetails']:
        print('The detected face is between ' + str(faceDetail['AgeRange']['Low'])
              + ' and ' + str(faceDetail['AgeRange']['High']) + ' years old')
        print('Here are the other attributes:')
        print(json.dumps(faceDetail, indent=4, sort_keys=True))

    if len(response['FaceDetails']) > 0:
        obj['name'] = picture.split(".")[0]
        obj['class'] = 'Profile Photo -- {} face detected'.format(
            len(response['FaceDetails']))
    else:
        obj['name'] = picture.split(".")[0]
        obj['class'] = 'UNCLASSIFIED'

    return obj


@app.route('/medical')
def medical():
    # Amazon Textract client
    textract = boto3.client('textract')
    documentName = "001.png"
    response = textract.detect_document_text(
        Document={
            'S3Object': {
                'Bucket': BUCKET,
                'Name': documentName
            }
        })
    text = ""
    for item in response["Blocks"]:
        if item["BlockType"] == "LINE":
            print('\033[94m' + item["Text"] + '\033[0m')
            text = text + " " + item["Text"]

    # Amazon Comprehend client
    comprehend = boto3.client(service_name='comprehendmedical')
    # Detect sentiment
    sentiment = comprehend.detect_entities(Text=text)
    #print ("\nSentiment\n========\n{}".format(sentiment.get('Sentiment')))
    #synTokArr = sentiment.get('SyntaxTokens')
    return str(sentiment)


def list_files(bucket):
    """
    Function to list files in a given S3 bucket
    """
    s3 = boto3.client('s3')
    contents = []
    for item in s3.list_objects(Bucket=bucket)['Contents']:
        contents.append(item)

    return contents


def download_file(file_name, bucket):
    """
    Function to download a given file from an S3 bucket
    """
    s3 = boto3.resource('s3')
    output = f"downloads/{file_name}"
    s3.Bucket(bucket).download_file(file_name, output)

    return output


def upload_file(file_name, bucket):
    """
    Function to upload a file to an S3 bucket
    """
    object_name = file_name
    s3_client = boto3.client('s3')
    response = s3_client.upload_file(file_name, bucket, object_name)

    return response


if __name__ == '__main__':
    app.run(debug=True)
