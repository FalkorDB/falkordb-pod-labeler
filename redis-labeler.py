#!/usr/bin/python3

# Copyright 2019 Redmart Pte Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import logging
import subprocess
import time
import os

from kubernetes import config, client

DEFAULT_CLUSTER_DOMAIN = "cluster.local"


def find_redis_and_label(k8s_api):

    # Get all pods
    pods = get_redis_pods(
        k8s_api,
    )

    if not pods:
        logging.info("No pods found")
        return

    # Get master from sentinel
    sentinel_host = f"{args.headless_name}.{args.namespace}.svc.{args.cluster_domain}"
    master = get_redis_master_pod_name(
        sentinel_host, args.sentinel_port, args.cluster_name
    )

    pods_with_roles = [
        (master, "master"),
    ]

    for pod in pods:
        if pod == master:
            continue
        pods_with_roles.append((pod, "slave"))

    for pod, role in pods_with_roles:
        label = generate_pod_label_body(role, args.domain)
        if not args.dry_run:
            label_redis_pods(k8s_api, pod, label)
        else:
            logging.info("Would apply label '%s' to %s", role, pod)


def get_redis_master_pod_name(redis_host, sentinel_port, cluster_name):
    logging.debug(
        f"Getting master pod for redis {redis_host}:{sentinel_port} {cluster_name}"
    )
    password = os.getenv(args.password_name)
    result_1 = ""
    if password is not None:
        result_1 = subprocess.run(
            [
                "redis-cli",
                "-h",
                redis_host,
                "-p",
                str(sentinel_port),
                "-a",
                password,
                "--no-auth-warning",
                "sentinel",
                "master",
                cluster_name,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=True,
        )
    else:
        result_1 = subprocess.run(
            [
                "redis-cli",
                "-h",
                redis_host,
                "-p",
                str(sentinel_port),
                "sentinel",
                "master",
                cluster_name,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=True,
        )

    logging.debug(f"Result: {result_1.stdout.decode('utf-8')}")

    result_2 = subprocess.run(
        ["sed", "-n", "4p"],
        input=result_1.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=True,
    )

    fqdn = str(result_2.stdout.decode("utf-8")).strip()
    logging.debug(f"FQDN: {fqdn}")

    pod_name = fqdn.split(".")[0]

    logging.debug(f"Master pod: {pod_name}")

    return pod_name


def get_redis_pods(k8s_api):
    # List pods in namespace
    logging.debug(
        f"Getting pods with selector {args.pod_selector} in namespace {args.namespace}"
    )
    pods = k8s_api.list_namespaced_pod(
        namespace="{}".format(args.namespace),
        label_selector="{}".format(args.pod_selector),
    )

    pods_names = []

    for pod in pods.items:
        pods_names.append(pod.metadata.name)

    logging.debug(f"Found pods: {pods_names}")

    return pods_names


def label_redis_pods(k8s_api, pod_name, label):
    logging.info(f"applying label '{label}' to {pod_name}")
    return k8s_api.patch_namespaced_pod(
        name=pod_name, namespace="{}".format(args.namespace), body=label
    )


def generate_pod_label_body(label, domain):
    patch_content = {
        "kind": "Pod",
        "apiVersion": "v1",
        "metadata": {"labels": {f"{domain}/role": label}},
    }
    return patch_content


parser = argparse.ArgumentParser(
    description="Checking redis pods and labelling them with master/ slave accordingly"
)
parser.add_argument("--dry-run", dest="dry_run", action="store_true", default=False)
parser.add_argument("--namespace", dest="namespace", required=False, default="redis")
parser.add_argument(
    "--pod-selector",
    dest="pod_selector",
    default="app.kubernetes.io/app=redis",
    required=False,
)
parser.add_argument("--redis-cluster-name", dest="cluster_name", default="mymaster")
parser.add_argument("--redis-headless-svc-name", dest="headless_name", required=True)
parser.add_argument(
    "--redis-sentinel_port", dest="sentinel_port", default=26379, required=False
)
parser.add_argument(
    "--redis-password-name", dest="password_name", default="REDIS_MASTER_PASSWORD"
)
parser.add_argument(
    "--cluster-domain",
    dest="cluster_domain",
    default=DEFAULT_CLUSTER_DOMAIN,
    required=False,
)
parser.add_argument(
    "--company-domain", dest="domain", default="redis.io", required=False
)
parser.add_argument("--config-file", dest="config_file", required=False)
parser.add_argument(
    "--incluster-config",
    dest="incluster_config",
    action="store_true",
    required=False,
    default=False,
)
parser.add_argument(
    "--insecure-skip-tls-verify",
    dest="skip_tls_verify",
    action="store_true",
    required=False,
    default=False,
)
parser.add_argument(
    "--verbose", dest="verbose", action="store_true", required=False, default=False
)
parser.add_argument("--update-period", dest="sleep_seconds", required=False, default=60)

args = parser.parse_args()

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.DEBUG if args.verbose else logging.INFO,
)

logging.captureWarnings(True)
logging.info("Starting redis replica labeler...")
logging.info(f"Dry run: {args.dry_run}")

if args.config_file is None:
    logging.info("Loading current kubernetes cluster config")
    config.load_incluster_config()
else:
    logging.info("Loading kubernetes from passed config file")
    config.load_kube_config(config_file=args.config_file)

logging.info(f"SSL Verify: {not args.skip_tls_verify}")
if args.skip_tls_verify:
    conf = client.Configuration()
    conf.verify_ssl = False
    conf.debug = False
    client.Configuration.set_default(conf)

v1Api = client.CoreV1Api()

while True:
    try:
        find_redis_and_label(v1Api)
        logging.info(f"Sleeping {args.sleep_seconds}...")
        time.sleep(int(args.sleep_seconds))
    except Exception as e:
        logging.error(f"Error: {e}")
        time.sleep(999999)
