# polaris-slack helm chart

- build docker image
- push to your docker repo
- use this helm chart to create cronjob in Kubernetes cluster (tested with EKS and ArgoCD)
- change main needed parameters in values.yaml ( better overwrite via ArgoCD UI parameters, ** not recommended to keep sensitive info in github repo ** )


