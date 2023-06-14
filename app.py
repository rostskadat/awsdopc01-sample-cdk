import os
from aws_cdk import (
                     aws_ec2 as ec2, 
                     aws_batch_alpha as batch,
                     aws_ecs as ecs,
                     aws_iam as iam,
                     App, Environment, Stack, CfnOutput, Size
                     )
from constructs import Construct

class BatchFargateStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        vpc_id = self.node.try_get_context("vpc_id")

        # This resource alone will create a private/public subnet in each AZ as well as nat/internet gateway(s)
        # vpc = ec2.Vpc(self, "VPC")
        vpc = ec2.Vpc.from_lookup(self, "vpc", vpc_id=vpc_id)

        # To create number of Batch Compute Environment
        environment_count = self.node.try_get_context("environment_count")

        # Create AWS Batch Job Queue
        self.batch_queue = batch.JobQueue(self, "JobQueue")

        # For loop to create Batch Compute Environments
        for i in range(environment_count):
            environment = batch.FargateComputeEnvironment(
                self, 
                "ComputeEnvironment" + str(i),
                vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_NAT),
                vpc=vpc
            )
            self.batch_queue.add_compute_environment(environment, i)

        # Task execution IAM role for Fargate
        task_execution_role = iam.Role(
            self, 
            "TaskExecutionRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy")])

        # Create Job Definition to submit job in batch job queue.
        batch_jobDef = batch.EcsJobDefinition(
            self, 
            "JobDefinition",
            container=batch.EcsFargateContainerDefinition(
                self, 
                "ContainerDefinition",
                image=ecs.ContainerImage.from_registry("public.ecr.aws/amazonlinux/amazonlinux:latest"),
                command=["sleep", "120"],
                memory=Size.mebibytes(512),
                cpu=0.25,
                execution_role=task_execution_role))

        # Output resources
        CfnOutput(self, "oBatchJobQueue",value=self.batch_queue.job_queue_name)
        CfnOutput(self, "oJobDefinition",value=batch_jobDef.job_definition_name)



app = App()
BatchFargateStack(app, "BatchFargateStack", env=Environment(
    account=os.environ["CDK_DEFAULT_ACCOUNT"],
    region=os.environ["CDK_DEFAULT_REGION"]))
app.synth()
