pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Backend Check') {
            steps {
                dir('backend') {
                    sh 'python -m pip install -r requirements.txt'
                    sh 'python manage.py check'
                }
            }
        }

        stage('Frontend Build') {
            steps {
                dir('frontend') {
                    sh 'npm install'
                    sh 'npm run build'
                }
            }
        }

        stage('AI Service Check') {
            steps {
                dir('ai-service') {
                    sh 'python -m pip install -r requirements.txt'
                    sh 'python -m compileall .'
                }
            }
        }
    }
}
