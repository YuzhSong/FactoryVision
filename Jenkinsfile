pipeline {
    agent any

    stages {

        // ==================================================================
        // Stage 1: Checkout
        // 拉取仓库代码
        // ==================================================================
        stage('Checkout') {
            steps {
                echo '========================================'
                echo '  Stage: Checkout'
                echo '  拉取仓库代码，确保工作区为本次构建对应提交'
                echo '========================================'
                checkout scm
                echo '[Checkout] 代码拉取完成'
            }
        }

        // ==================================================================
        // Stage 2: Backend Check
        // 检查 Django 项目配置是否正确（不运行测试）
        // ==================================================================
        stage('Backend Check') {
            steps {
                echo '========================================'
                echo '  Stage: Backend Check'
                echo '  安装 Django 依赖并执行系统检查'
                echo '========================================'
                dir('backend') {
                    echo '[Backend Check] 安装后端依赖...'
                    script {
                        if (isUnix()) {
                            sh 'python -m pip install -r requirements.txt'
                        } else {
                            bat 'python -m pip install -r requirements.txt'
                        }
                    }
                    echo '[Backend Check] 执行 python manage.py check...'
                    script {
                        if (isUnix()) {
                            sh 'python manage.py check'
                        } else {
                            bat 'python manage.py check'
                        }
                    }
                }
                echo '[Backend Check] Django 配置检查通过'
            }
        }

        // ==================================================================
        // Stage 3: Backend Test
        // 运行 Django 单元测试（8 个 tests.py，覆盖各 app）
        // ==================================================================
        stage('Backend Test') {
            steps {
                echo '========================================'
                echo '  Stage: Backend Test'
                echo '  运行 Django 单元测试'
                echo '========================================'
                dir('backend') {
                    echo '[Backend Test] 执行 python manage.py test...'
                    script {
                        if (isUnix()) {
                            sh 'python manage.py test --verbosity=2'
                        } else {
                            bat 'python manage.py test --verbosity=2'
                        }
                    }
                }
                echo '[Backend Test] 测试执行完成'
            }
        }

        // ==================================================================
        // Stage 4: Frontend Build
        // 构建 Vue 3 + Vite 前端项目
        // 注意：不运行 npm lint / npm test，因为 package.json 中暂未配置
        // ==================================================================
        stage('Frontend Build') {
            steps {
                echo '========================================'
                echo '  Stage: Frontend Build'
                echo '  安装前端依赖并执行生产构建 (Vite)'
                echo '========================================'
                dir('frontend') {
                    echo '[Frontend Build] 安装前端依赖 (npm install)...'
                    script {
                        if (isUnix()) {
                            sh 'npm install'
                        } else {
                            bat 'npm install'
                        }
                    }
                    echo '[Frontend Build] 执行 npm run build...'
                    script {
                        if (isUnix()) {
                            sh 'npm run build'
                        } else {
                            bat 'npm run build'
                        }
                    }
                }
                echo '[Frontend Build] 前端构建完成，产物位于 frontend/dist/'
            }
        }

        // ==================================================================
        // Stage 5: AI Service Test
        // 运行 AI 服务（FastAPI）的单元测试
        // 使用 unittest discover 自动发现 tests/ 目录下的测试用例
        // ==================================================================
        stage('AI Service Test') {
            steps {
                echo '========================================'
                echo '  Stage: AI Service Test'
                echo '  安装 FastAPI 依赖并运行单元测试'
                echo '========================================'
                dir('ai-service') {
                    echo '[AI Service Test] 安装 AI 服务依赖...'
                    script {
                        if (isUnix()) {
                            sh 'python -m pip install -r requirements.txt'
                        } else {
                            bat 'python -m pip install -r requirements.txt'
                        }
                    }
                    echo '[AI Service Test] 执行 python -m unittest discover tests...'
                    script {
                        if (isUnix()) {
                            sh 'python -m unittest discover tests'
                        } else {
                            bat 'python -m unittest discover tests'
                        }
                    }
                }
                echo '[AI Service Test] AI 服务测试完成'
            }
        }

        // ==================================================================
        // Stage 6: Archive Artifacts
        // 归档前端构建产物 (dist/) 及其他日志
        // 归档失败不影响主流程（try-catch 保护）
        // ==================================================================
        stage('Archive Artifacts') {
            steps {
                echo '========================================'
                echo '  Stage: Archive Artifacts'
                echo '  归档构建产物，失败不影响主流程'
                echo '========================================'
                script {
                    // 归档前端 dist 目录
                    try {
                        archiveArtifacts artifacts: 'frontend/dist/**', fingerprint: true
                        echo '[Archive] 前端 dist/ 归档成功'
                    } catch (Exception e) {
                        echo "[Archive] 前端 dist/ 归档失败（非致命）: ${e.getMessage()}"
                    }
                }
                echo '[Archive Artifacts] 归档阶段结束'
            }
        }

        // ==================================================================
        // Stage 7: Docker Build（预留）
        // 当前为占位阶段，后续需为三个服务分别创建 Dockerfile
        // ==================================================================
        stage('Docker Build') {
            steps {
                echo '========================================'
                echo '  Stage: Docker Build [预留/占位]'
                echo '========================================'
                echo ''
                echo '  当前状态：暂不执行 docker build'
                echo ''
                echo '  启用前需新增以下文件：'
                echo '    1. backend/Dockerfile'
                echo '       - 基于 python:3.14-slim'
                echo '       - 使用 gunicorn 替代 runserver'
                echo '       - 示例: docker build -t factoryvision-backend ./backend'
                echo ''
                echo '    2. frontend/Dockerfile'
                echo '       - 多阶段构建：node 构建 + nginx 提供静态文件'
                echo '       - 示例: docker build -t factoryvision-frontend ./frontend'
                echo ''
                echo '    3. ai-service/Dockerfile'
                echo '       - 基于 python:3.14-slim'
                echo '       - 使用 uvicorn（不带 --reload）'
                echo '       - 示例: docker build -t factoryvision-ai-service ./ai-service'
                echo ''
                echo '  当前 docker-compose.yml 偏本地开发环境，'
                echo '  不适合直接用于生产构建。'
                echo '  生产环境建议新增 docker-compose.prod.yml。'
                echo ''
                echo '  Docker Build 阶段已跳过。'
                echo '========================================'
            }
        }

        // ==================================================================
        // Stage 8: Deploy Test Environment（预留）
        // 当前为占位阶段，后续需完善部署配置
        // ==================================================================
        stage('Deploy Test Environment') {
            steps {
                echo '========================================'
                echo '  Stage: Deploy Test Environment [预留/占位]'
                echo '========================================'
                echo ''
                echo '  当前状态：暂不执行部署'
                echo ''
                echo '  当前 docker-compose.yml 的问题：'
                echo '    1. 使用开发服务器（runserver / vite dev / --reload）'
                echo '    2. 挂载源码卷（不适合生产）'
                echo '    3. 数据库使用 SQLite（生产需 MySQL）'
                echo ''
                echo '  启用前需要：'
                echo '    1. 新增 docker-compose.prod.yml'
                echo '       - 使用预构建的 Docker 镜像'
                echo '       - 前端通过 Nginx 提供静态文件'
                echo '       - 后端使用 gunicorn'
                echo '       - AI 服务去掉 --reload'
                echo '    2. 配置生产环境变量'
                echo '       - DJANGO_DEBUG=False'
                echo '       - DB_ENGINE=mysql'
                echo '       - DB_HOST/DB_USER/DB_PASSWORD/DB_PORT'
                echo '    3. 部署命令示例：'
                echo '       docker compose -f docker-compose.prod.yml up -d'
                echo ''
                echo '  Deploy Test Environment 阶段已跳过。'
                echo '========================================'
            }
        }
    }

    // ====================================================================
    // Post Actions
    // 无论流水线成功或失败，都输出汇总信息
    // ====================================================================
    post {
        always {
            echo '========================================'
            echo '  Pipeline 执行结束'
            echo '  请检查上方各阶段日志确认执行结果'
            echo '========================================'
        }
        success {
            echo '✓ 所有阶段执行成功！'
        }
        failure {
            echo '✗ 部分阶段执行失败，请查看上方日志定位问题'
        }
    }
}
