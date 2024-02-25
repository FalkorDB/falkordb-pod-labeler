import argparse
import logging
import subprocess
import time
import os

from kubernetes import config, client

DEFAULT_CLUSTER_DOMAIN = "cluster.local"


def find_falkordb_and_label(k8s_api):

    # Get all pods
    pods = get_falkordb_pods(
        k8s_api,
    )

    if not pods:
        logging.info("No pods found")
        return

    # Get master from sentinel
    sentinel_host = f"{args.headless_name}.{args.namespace}.svc.{args.cluster_domain}"
    master = get_falkordb_master_pod_name(
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
            label_falkordb_pods(k8s_api, pod, label)
        else:
            logging.info("Would apply label '%s' to %s", role, pod)


def get_falkordb_master_pod_name(falkordb_host, sentinel_port, cluster_name):
    logging.debug(
        f"Getting master pod for falkordb {falkordb_host}:{sentinel_port} {cluster_name}"
    )
    password = os.getenv(args.password_name)
    result_1 = ""
    if password is not None:
        result_1 = subprocess.run(
            [
                "timeout",
                args.sleep_seconds,
                "redis-cli",
                "-h",
                falkordb_host,
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
                "timeout",
                args.sleep_seconds,
                "redis-cli",
                "-h",
                falkordb_host,
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


def get_falkordb_pods(k8s_api):
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


def label_falkordb_pods(k8s_api, pod_name, label):
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
    description="Checking falkordb pods and labelling them with master/ slave accordingly"
)
parser.add_argument("--dry-run", dest="dry_run", action="store_true", default=False)
parser.add_argument("--namespace", dest="namespace", required=False, default="falkordb")
parser.add_argument(
    "--pod-selector",
    dest="pod_selector",
    default="app.kubernetes.io/instance=falkordb",
    required=False,
)
parser.add_argument("--falkordb-cluster-name", dest="cluster_name", default="mymaster")
parser.add_argument("--falkordb-headless-svc-name", dest="headless_name", required=True)
parser.add_argument(
    "--falkordb-sentinel_port", dest="sentinel_port", default=26379, required=False
)
parser.add_argument(
    "--falkordb-password-name", dest="password_name", default="FALKORDB_MASTER_PASSWORD"
)
parser.add_argument(
    "--cluster-domain",
    dest="cluster_domain",
    default=DEFAULT_CLUSTER_DOMAIN,
    required=False,
)
parser.add_argument(
    "--company-domain", dest="domain", default="falkordb.com", required=False
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
logging.info("Starting falkordb replica labeler...")
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
        find_falkordb_and_label(v1Api)
        logging.info(f"Sleeping {args.sleep_seconds}...")
        time.sleep(int(args.sleep_seconds))
    except Exception as e:
        logging.error(f"Error: {e}")
