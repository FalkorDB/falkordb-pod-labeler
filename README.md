# falkordb-pod-labeler

Docker image for find and label the FalkorDB pods in a kubernetes cluster according to the role (master, slave) 

[Docker Image Link](https://hub.docker.com/repository/docker/falkordb/falkordb-pod-labeler)

## Description
A simple python script to find the FalkorDB pods in Kubernetes for the given labels and label them according to the rule.

`redis-cli -h falkordb-ha.falkordb -p 26379 sentinel master mymaster` - used to get the falkordb master service details

`sed -n 4p` - used to get the FQDN from the above command

Those pods updated with the labels `{domain}/role=master`, `{domain}/role=slave` accordingly.

## Arguments

| Argument name             | Description                                         | Default      | 
|---------------------------|-----------------------------------------------------|--------------|
|`--falkordb-cluster-name`     | falkordb sentinel master-group-name   |     mymaster     |
|`--falkordb-headless-svc-name`| headless service name of the falkordb (must required)  |              |
|`--namespace`              | namespace of the FalkorDB deployment                | falkordb        |
|`--pod-selector`           | key=value of to match labels and get the falkordb pods | app.kubernetes.io/instance=falkordb |
|`--falkordb-sentinel_port`    | falkordb sentinel port                                 | 26379        |
|`--update-period`          | How frequent this should update the labels (seconds)| 60           |
|`--company-domain`         | company domain to make label key (example.com/role) | falkordb.com     |
|`--config-file`            | path to kube config file                            |       -      |
|`--incluster-config`       | load in-cluster kube config                         | True         |
|`--insecure-skip-tls-verify`| skip tls verification                              | False        |
|`--verbose`                 | enable detailed output in the logs                 | False        |
|`--falkordb-password-name`                 | the environment variable for the password                 | FALKORDB_MASTER_PASSWORD        |
