node('haimaxy-jnlp') {
    stage('Clone') {
        echo "1.Clone 代码"
        git url: "https://github.com/yangmv/SuperCMDB.git"
        script {
            build_tag = sh(returnStdout: true, script: 'git rev-parse --short HEAD').trim()
        }
    }
    stage('Test') {
      echo "2.代码测试[PAAS]"
    }
    stage('Build') {
        echo "3.构建打包 Docker 镜像"
        sh "docker build -t harbor-k8s.shinezone.com/ops/flask-demo:${build_tag} ."
    }
    stage('Push') {
        echo "4.推送 Docker 镜像到仓库"
        withCredentials([usernamePassword(credentialsId: 'dockerHubSZ', passwordVariable: 'dockerHubSZPassword', usernameVariable: 'dockerHubSZUser')]) {
            sh "docker login -u ${dockerHubSZUser} -p ${dockerHubSZPassword} https://harbor-k8s.shinezone.com"
            sh "docker push harbor-k8s.shinezone.com/ops/flask-demo:${build_tag}"
        }
    }
    stage('YAML') {
        echo "5.YAML配置"
        sh "sed -i 's/<BUILD_TAG>/${build_tag}/' flask-demo-deploy.yaml"
        sh "sed -i 's/<PORT>/${port}/' flask-demo-deploy.yaml"
        sh "sed -i 's/<PORT>/${port}/' flask-demo-ingress.yaml"
        sh "sed -i 's/<DOMAIN>/${domain}/' flask-demo-ingress.yaml"
    }
    stage('Deploy') {
        echo "6.开始部署"
        //if (userInput == "Dev") {
            //sh "kubectl apply -f flask-demo-deploy.yaml -n dev"
        //} else if (userInput == "QA"){
            //sh "kubectl apply -f flask-demo-deploy.yaml -n qa"
        //} else {
            //sh "kubectl apply -f flask-demo-deploy.yaml -n release"
        //}
        sh "kubectl apply -f flask-demo-deploy.yaml -n ${namespace}"
        sh "kubectl apply -f flask-demo-ingress.yaml -n ${namespace}"
    }
}