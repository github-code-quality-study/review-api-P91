import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.corpus import stopwords
from urllib.parse import parse_qs, urlparse
import urllib.parse
import json
import pandas as pd
from datetime import datetime
import uuid
import os
from typing import Callable, Any
from wsgiref.simple_server import make_server

nltk.download('vader_lexicon', quiet=True)
nltk.download('punkt', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)
nltk.download('stopwords', quiet=True)

adj_noun_pairs_count = {}
sia = SentimentIntensityAnalyzer()
stop_words = set(stopwords.words('english'))

reviews = pd.read_csv('data/reviews.csv').to_dict('records')

class ReviewAnalyzerServer:
    def __init__(self) -> None:
        # This method is a placeholder for future initialization logic
        pass

    def analyze_sentiment(self, review_body):
        sentiment_scores = sia.polarity_scores(review_body)
        return sentiment_scores


    def handle_post(self,environ):
        body=int(environ.get('CONTENT_LENGTH',0))
        data=environ['wsgi.input'].read(body).decode('utf-8')

        parameters={}

        for d in data.split('&'):
            if '=' in d:
                key,value= d.split('=')
                value2=""
                for v in value:
                    if v=='+':
                        value2+=' '
                    else:
                        value2+=v
                value2 = urllib.parse.unquote(value2)  # Properly decode URL-encoded characters
                parameters[key] = value
                parameters[key]=value2
            
        
        if 'Location' not in parameters or 'ReviewBody' not in parameters:
            return '400 Bad Request', b'Missing Location or ReviewBody'

        valid_locations=locations = [
            "Albuquerque, New Mexico",
            "Carlsbad, California",
            "Chula Vista, California",
            "Colorado Springs, Colorado",
            "Denver, Colorado",
            "El Cajon, California",
            "El Paso, Texas",
            "Escondido, California",
            "Fresno, California",
            "La Mesa, California",
            "Las Vegas, Nevada",
            "Los Angeles, California",
            "Oceanside, California",
            "Phoenix, Arizona",
            "Sacramento, California",
            "Salt Lake City, Utah",
            "Salt Lake City, Utah",
            "San Diego, California",
            "Tucson, Arizona"
        ]

        if parameters['Location'] not in valid_locations:  
            print("----------------------------------------------")
            print('LOCATION: ',parameters['Location'])
            return '400 Bad Request', b'Invalid Location'
        
        review={
            'ReviewId': uuid.uuid4().hex,
            'Location': parameters['Location'],
            'ReviewBody': parameters['ReviewBody'],
            'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        reviews.append(review)
        return '201 Created', json.dumps(review).encode('utf-8')


    def __call__(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> bytes:
        """
        The environ parameter is a dictionary containing some useful
        HTTP request information such as: REQUEST_METHOD, CONTENT_LENGTH, QUERY_STRING,
        PATH_INFO, CONTENT_TYPE, etc.
        """

        if environ["REQUEST_METHOD"] == "GET":
            # Create the response body from the reviews and convert to a JSON byte string

            query= parse_qs(environ['QUERY_STRING'])
            location= query.get('location',[None])[0]
            start=query.get('start_date',[None])[0]
            end=query.get('end_date',[None])[0]

            reviews_to_return = reviews
            if location:
                reviews_to_return=[r for r in reviews_to_return if r['Location']==location]
            
            if start:
                start_date = datetime.strptime(start, '%Y-%m-%d')
                reviews_to_return = [r for r in reviews_to_return if datetime.strptime(r['Timestamp'], '%Y-%m-%d %H:%M:%S') >= start_date]

            if end:
                end_date= datetime.strptime(end, '%Y-%m-%d')
                reviews_to_return = [r for r in reviews_to_return if datetime.strptime(r['Timestamp'], '%Y-%m-%d %H:%M:%S') <= end_date]

            for r in reviews_to_return:
                sentiment= self.analyze_sentiment(review_body=r['ReviewBody'])
                r['sentiment']=sentiment

            sorted_reviews= sorted(reviews_to_return,key=lambda x:x['sentiment']['compound'], reverse=True)
            response_body = json.dumps(sorted_reviews, indent=2).encode("utf-8")
                        

            # Set the appropriate response headers
            start_response("200 OK", [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(response_body)))
             ])
            
            return [response_body]


        if environ["REQUEST_METHOD"] == "POST":
            status, response_body = self.handle_post(environ)
            start_response(status, [
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(response_body)))
            ])
            return [response_body]

if __name__ == "__main__":
    app = ReviewAnalyzerServer()
    port = os.environ.get('PORT', 8000)
    with make_server("", port, app) as httpd:
        print(f"Listening on port {port}...")
        httpd.serve_forever()