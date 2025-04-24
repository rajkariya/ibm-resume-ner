from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from bson.objectid import ObjectId
from django.shortcuts import render, redirect
from pymongo import MongoClient

# Initialize MongoDB client
client = MongoClient('mongodb://localhost:27017/')
db = client['resume_ner']

def landing_page(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'landing.html')

@login_required
def get_applications(request, job_id):
    try:
        # Create pipeline for aggregation
        pipeline = [
            {
                '$match': {
                    'job_id': job_id
                }
            },
            {
                '$lookup': {
                    'from': 'results',
                    'let': {'resume_uuid': '$resume_uuid'},
                    'pipeline': [
                        {
                            '$match': {
                                '$expr': {
                                    '$eq': ['$resume_uuid', '$$resume_uuid']
                                }
                            }
                        }
                    ],
                    'as': 'results'
                }
            },
            {
                '$project': {
                    '_id': 1,
                    'name': 1,
                    'email': 1,
                    'phone': 1,
                    'resume_url': 1,
                    'applied_at': 1,
                    'status': 1,
                    'resume_uuid': 1,
                    'results': {
                        '$cond': {
                            'if': {'$gt': [{'$size': '$results'}, 0]},
                            'then': {'$arrayElemAt': ['$results', 0]},
                            'else': None
                        }
                    }
                }
            }
        ]

        # Execute aggregation
        applications = list(db.applications.aggregate(pipeline))

        # Format the response
        formatted_applications = []
        for app in applications:
            app_data = {
                '_id': str(app['_id']),
                'name': app.get('name', ''),
                'email': app.get('email', ''),
                'phone': app.get('phone', ''),
                'resume_url': app.get('resume_url', ''),
                'applied_at': app.get('applied_at', ''),
                'status': app.get('status', 'pending'),
                'resume_uuid': app.get('resume_uuid', '')
            }

            # Add results data if available
            if app.get('results'):
                app_data['results'] = {
                    'score': app['results'].get('score', 0),
                    'processed_at': app['results'].get('processed_at', ''),
                    'overview': app['results'].get('overview', ''),
                    'entities': app['results'].get('entities', {})
                }

            formatted_applications.append(app_data)

        return JsonResponse({
            'success': True,
            'data': formatted_applications
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def get_application_results(request, application_id):
    try:
        # Get the application
        application = db.applications.find_one({'_id': ObjectId(application_id)})
        if not application:
            return JsonResponse({'success': False, 'error': 'Application not found'}, status=404)

        # Get the results using resume_uuid
        results = db.results.find_one({'resume_uuid': application.get('resume_uuid')})
        if not results:
            return JsonResponse({'success': False, 'error': 'Results not found'}, status=404)

        # Prepare the response data
        response_data = {
            'name': application.get('name', ''),
            'email': application.get('email', ''),
            'phone': application.get('phone', ''),
            'score': results.get('score', 0),
            'processed_at': results.get('processed_at', ''),
            'overview': results.get('overview', ''),
            'entities': results.get('entities', {})
        }

        return JsonResponse({'success': True, 'data': response_data})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

