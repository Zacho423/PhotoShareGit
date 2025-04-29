from flask import Flask, render_template, request, redirect, url_for
import boto3
import uuid
import time
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta

app = Flask(__name__)

# Set AWS Region
AWS_REGION = 'us-east-2'

# Initialize AWS clients
s3 = boto3.client('s3', region_name=AWS_REGION)
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
table = dynamodb.Table('PhotoSubmissions')

# Your actual S3 bucket name here
BUCKET = 'photoshare-bucket101'

# Scheduler to delete old photos
scheduler = BackgroundScheduler()

def delete_old_photos():
    now = int(time.time())
    ten_minutes_ago = now - 600  # 10 minutes ago in seconds

    # Scan DynamoDB for images older than 10 minutes
    response = table.scan()
    for item in response['Items']:
        if item['Timestamp'] < ten_minutes_ago:
            # Delete the photo from S3
            s3.delete_object(Bucket=BUCKET, Key=item['ImageKey'])

            # Also delete the metadata from DynamoDB
            table.delete_item(Key={'ImageKey': item['ImageKey']})

            print(f"Deleted {item['ImageKey']} as it was older than 10 minutes.")

# Start the background scheduler
scheduler.add_job(delete_old_photos, 'interval', minutes=1)  # Run every minute
scheduler.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['image']
    submitter = request.form['submitter']
    image_key = f"{uuid.uuid4()}_{file.filename}"
    timestamp = int(time.time())

    # Upload to S3
    s3.upload_fileobj(file, BUCKET, image_key)

    # Log to DynamoDB
    table.put_item(Item={
        'ImageKey': image_key,
        'Timestamp': timestamp,
        'Submitter': submitter
    })

    return redirect(url_for('success', key=image_key))

@app.route('/success')
def success():
    key = request.args.get('key')
    image_url = f"https://{BUCKET}.s3.{AWS_REGION}.amazonaws.com/{key}"
    return f"<h2>Upload successful!</h2><img src='{image_url}' width='300'>"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
