terraform {
	required_providers {
		aws = {
			source = "hashicorp/aws"
			version = "~> 5.0"
		}
	}
}

provider "aws" {
	region = "eu-central-1"
}

resource "aws_vpc" "main" {
	cidr_block = "10.0.0.0/16"

	tags = {
		Name = "fastapi-vpc"
	}
}

resource "aws_subnet" "a" {
	vpc_id = aws_vpc.main.id
	cidr_block = "10.0.1.0/24"
	availability_zone = "eu-central-1a"

	tags = {
		Name = "fastapi-subnet-a"
	}
}

resource "aws_subnet" "b" {
	vpc_id = aws_vpc.main.id
	cidr_block = "10.0.2.0/24"
	availability_zone = "eu-central-1b"

	tags = {
		Name = "fastapi-subnet-b"
	}
}

resource "aws_internet_gateway" "main" {
	vpc_id = aws_vpc.main.id

	tags = {
		Name = "fastapi-igw"
	}
}

resource "aws_route_table" "main" {
	vpc_id = aws_vpc.main.id

	route {
		cidr_block = "0.0.0.0/0"
		gateway_id = aws_internet_gateway.main.id
	}

	tags = {
		Name = "fastapi-rt"
	}
}

resource "aws_route_table_association" "a" {
	subnet_id = aws_subnet.a.id
	route_table_id = aws_route_table.main.id
}

resource "aws_route_table_association" "b" {
	subnet_id = aws_subnet.b.id
	route_table_id = aws_route_table.main.id
}

resource "aws_security_group" "ec2" {
	name = "fastapi-ec2-sg"
	description = "Allow HTTP and SSH"
	vpc_id = aws_vpc.main.id

	ingress {
		description = "HTTP"
		from_port = 80
		to_port = 80
		protocol = "tcp"
		cidr_blocks = ["0.0.0.0/0"]
}

	ingress {
		description = "SSH"
		from_port = 22
		to_port = 22
		protocol = "tcp"
		cidr_blocks = ["0.0.0.0/0"]
	}

	egress {
		from_port = 0
		to_port = 0
		protocol = "-1"
		cidr_blocks = ["0.0.0.0/0"]
	}

	tags = {
		Name = "fastapi-ec2-sg"
	}
}

resource "aws_security_group" "rds" {
	name = "fastapi-rds-sg"
	description = "Allow PostgreSQL from EC2"
	vpc_id = aws_vpc.main.id

	ingress {
		description = "PostgreSQL from EC2"
		from_port = 5432
		to_port = 5432
		protocol = "tcp"
		security_groups = [aws_security_group.ec2.id]
	}

	tags = {
		Name = "fastapi-rds-sg"
	}
}

resource "aws_db_subnet_group" "main" {
	name = "fastapi-db-subnet-group"
	subnet_ids = [aws_subnet.a.id, aws_subnet.b.id]

	tags = {
		Name = "fastapi-db-subnet-group"
	}
}

variable "db_password" {
  type      = string
  sensitive = true
}

resource "aws_db_instance" "main" {
	identifier = "fastapi-db"
	engine = "postgres"
	instance_class = "db.t3.micro"
	allocated_storage = 20

	username = "postgres"
	password = var.db_password
	
	db_subnet_group_name = aws_db_subnet_group.main.name
	vpc_security_group_ids = [aws_security_group.rds.id]
	publicly_accessible = false
	skip_final_snapshot = true

	tags = {
		Name = "fastapi-db"
	}
}

resource "aws_ecr_repository" "main" {
	name = "fastapi-app"

	tags = {
		Name = "fastapi-app"
	}
}

resource "aws_iam_role" "ec2" {
	name = "fastapi-ec2-role"

	assume_role_policy = jsonencode({
		Version = "2012-10-17"
		Statement = [
			{
				Effect = "Allow"
				Principal = {
					Service = "ec2.amazonaws.com"
				}
				Action = "sts:AssumeRole"
			}
		]
	})
}

resource "aws_iam_role_policy_attachment" "ecr" {
	role = aws_iam_role.ec2.name
	policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

resource "aws_iam_instance_profile" "ec2" {
	name = "fastapi-ec2-profile"
	role = aws_iam_role.ec2.name
}

resource "aws_instance" "main" {
	ami = "ami-0abe96a6773a37eb1"
	instance_type = "t3.micro"
	subnet_id = aws_subnet.a.id
	vpc_security_group_ids = [aws_security_group.ec2.id]
	iam_instance_profile = aws_iam_instance_profile.ec2.name
	key_name = "twitter-key"

	associate_public_ip_address = true

	user_data = <<-EOF
		#!/bin/bash
		yum update -y
		yum install -y docker
		systemctl start docker
		systemctl enable docker
		usermod -aG docker ec2-user
	EOF

	tags = {
		Name = "fastapi-server"
	}
}

output "ec2_public_ip" {
  value = aws_instance.main.public_ip
}

output "rds_endpoint" {
  value = aws_db_instance.main.endpoint
}

output "ecr_url" {
  value = aws_ecr_repository.main.repository_url
}