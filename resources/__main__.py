import pulumi
import pulumi_gcp as gcp
import pulumiverse_time as time


from models import DataContract
import os


FOLDER_ID = "210121159154"
BILLING_ACCOUNT = "01BD03-925DA4-E3DBF1"


def kebab_case_to_snake_case(name: str) -> str:
    return name.replace("-", "_")


data_contract_dir = "../contracts/"
data_contracts: list[DataContract] = []
for filename in os.listdir(data_contract_dir):
    if filename.endswith(".yaml"):
        filepath = os.path.join(data_contract_dir, filename)
        data_contracts.append(DataContract(filepath))

for data_contract in data_contracts:
    project = gcp.organizations.Project(
        data_contract.name(),
        folder_id=FOLDER_ID,
        billing_account=BILLING_ACCOUNT,
    )

    bigquery_service = gcp.projects.Service(
        f"{data_contract.name()}_bigquery_service",
        project=project.project_id,
        service="bigquery.googleapis.com",
        disable_on_destroy=False,
    )
    wait_bigquery_service = time.Sleep(
        bigquery_service._name,
        create_duration="15s",
        opts=pulumi.ResourceOptions(depends_on=[bigquery_service]),
    )

    dataset_id = kebab_case_to_snake_case(data_contract.name())
    dataset = gcp.bigquery.Dataset(
        data_contract.name(),
        project=project.project_id,
        location="US",
        dataset_id=dataset_id,
        delete_contents_on_destroy=True,
        opts=pulumi.ResourceOptions(
            depends_on=[wait_bigquery_service], delete_before_replace=True
        ),
    )

    for model_name, model in data_contract.models().items():
        table = gcp.bigquery.Table(
            f"{data_contract.name()}_{model_name}",
            project=project.project_id,
            dataset_id=dataset.dataset_id,
            table_id=model_name,
            schema=data_contract.bigquery_schema(model_name),
            deletion_protection=False,
            opts=pulumi.ResourceOptions(delete_before_replace=True),
        )

    bucket = gcp.storage.Bucket(
        data_contract.name(),
        project=project.project_id,
        location="us",
    )
