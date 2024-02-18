# redis-pod-labeler

Docker image for find and label the redis pods in a kubernetes cluster according to the role (master, slave) 

[Docker Image Link](https://hub.docker.com/repository/docker/dudizimber/redis-pod-labeler)

## Description
A simple python script to find the redis pods in Kubernetes for the given labels and label them according to the rule.

`redis-cli -h redis-ha.redis -p 26379 sentinel master mymaster` - used to get the redis master service details

`sed -n 4p` - used to get the FQDN from the above command

`grep -oP "^([^.]+)"` - used to get the pod name from the FQDN

Those pods updated with the labels `{domain}/role=master`, `{domain}/role=slave` accordingly.

## Arguments

| Argument name             | Description                                         | Default      | 
|---------------------------|-----------------------------------------------------|--------------|
|`--redis-cluster-name`     | redis sentinel master-group-name (must required)    |              |
|`--redis-headless-svc-name`| headless service name of the redis (must required)  |              |
|`--namespace`              | namespace of the redis-ha deployment                | redis        |
|`--pod-selector`           | key=value of to match labels and get the redis pods | app.kubernetes.io/app=redis |
|`--redis-sentinel_port`    | redis sentinel port                                 | 26379        |
|`--update-period`          | How frequent this should update the labels (seconds)| 60           |
|`--company-domain`         | company domain to make label key (example.com/role) | redis.io     |
|`--config-file`            | path to kube config file                            |       -      |
|`--incluster-config`       | load in-cluster kube config                         | True         |
|`--insecure-skip-tls-verify`| skip tls verification                              | False        |
|`--verbose`                 | enable detailed output in the logs                 | False        |
