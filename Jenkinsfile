pipeline {
    agent any

    options {
        disableConcurrentBuilds()
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    environment {
        DEPLOY_ENV_FILE = 'deploy/.env.prod'
        COMPOSE_FILE = 'deploy/docker-compose.prod.yml'
        COMPOSE_PROJECT_NAME = 'factoryvision'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                sh 'git rev-parse --short HEAD'
            }
        }

        stage('Validate cloud-side code') {
            steps {
                sh 'test -f "$DEPLOY_ENV_FILE"'
                sh 'docker compose --env-file "$DEPLOY_ENV_FILE" -f "$COMPOSE_FILE" config >/dev/null'
                dir('frontend') {
                    sh 'npm ci'
                    sh 'npm run build'
                }
                dir('backend') {
                    sh 'python3 -m pip install -r requirements.txt'
                    sh 'python3 manage.py check'
                }
            }
        }

        stage('Build production images') {
            steps {
                sh 'docker compose --env-file "$DEPLOY_ENV_FILE" -f "$COMPOSE_FILE" build frontend backend'
            }
        }

        stage('Deploy cloud stack') {
            steps {
                sh 'docker compose --env-file "$DEPLOY_ENV_FILE" -f "$COMPOSE_FILE" up -d db backend frontend'
                sh 'docker compose --env-file "$DEPLOY_ENV_FILE" -f "$COMPOSE_FILE" exec -T backend python manage.py migrate --noinput'
                sh 'docker compose --env-file "$DEPLOY_ENV_FILE" -f "$COMPOSE_FILE" exec -T backend python manage.py collectstatic --noinput'
            }
        }

        stage('Health check') {
            steps {
                sh 'docker compose --env-file "$DEPLOY_ENV_FILE" -f "$COMPOSE_FILE" ps'
                sh 'curl -fsS http://127.0.0.1:18080/ >/dev/null'
                sh 'curl -fsS http://127.0.0.1:18080/api/health/ >/dev/null'
            }
        }

        stage('Cleanup dangling images') {
            steps {
                sh 'docker image prune -f'
            }
        }
    }

    post {
        always {
            sh 'docker compose --env-file "$DEPLOY_ENV_FILE" -f "$COMPOSE_FILE" ps || true'
        }
        failure {
            echo 'Deployment failed. Existing running containers and database volumes were not removed.'
            echo 'Inspect logs: docker compose --env-file deploy/.env.prod -f deploy/docker-compose.prod.yml logs --tail=200'
        }
    }
}
