## Usage Documentation

### Starting Point: Defining a Permission Matrix
To effectively utilize the K8s IAM Operator, it's crucial to first define a permission matrix. This matrix will outline the permissions for various roles and resources within your Kubernetes environment, ensuring a clear and organized access control system.

### User Permissions Matrix 
The following matrices illustrate the permissions assigned to different ClusterRoles (`observer`, `admin`, `developer`, `namespace-list`) across various operations (like get, list, watch, etc.) in Wikimove.

| ClusterRole    | get | list | watch | create | update | patch | delete |
|:-------------- |:---:|:----:|:-----:|:------:|:------:|:-----:|:------:|
| observer       |  ✓  |   ✓  |   ✓   |    ✘   |    ✘   |   ✘   |    ✘   |
| admin          |  ✓  |   ✓  |   ✓   |    ✓   |    ✓   |   ✓   |    ✓   |
| developer      |  ✓  |   ✓  |   ✓   |    ✓   |    ✓   |   ✓   |    ✓   |
| namespace-list |  ✓  |   ✓  |   ✘   |    ✘   |    ✘   |   ✘   |    ✘   |

The following matrix shows the permissions for different groups (`developer`, `observer`, `admin`) across environments (`dev`, `test`, `prod`).

| group     | dev | test | prod |
|:--------- |:---:|:----:|:----:|
| developer |  ✓  |   ✓  |   ✘  |
| observer  |  ✓  |   ✓  |   ✘  |
| admin     |  ✓  |   ✓  |   ✓  |

Resource-wise permissions are outlined as follows:

|resources         | admin     | developer | observer  | namespace-list|
|:-----------------|:---------:|:---------:|:---------:|:-------------:|
| pods             |     ✓     |     ✓     |     ✓     |       ✘       |
| pods/logs        |     ✓     |     ✓     |     ✘     |       ✘       |
| pods/portforward |     ✓     |     ✓     |     ✘     |       ✘       |
| services         |     ✓     |     ✓     |     ✓     |       ✘       |
| ingresses        |     ✓     |     ✓     |     ✓     |       ✘       |
| deployments      |     ✓     |     ✓     |     ✓     |       ✘       |
| DaemonSets       |     ✓     |     ✓     |     ✓     |       ✘       |
| StatefulSets     |     ✓     |     ✓     |     ✓     |       ✘       |
| ReplicaSets      |     ✓     |     ✓     |     ✘     |       ✘       |
| CronJobs         |     ✓     |     ✓     |     ✓     |       ✘       |
| Jobs             |     ✓     |     ✓     |     ✓     |       ✘       |
| secrets          |     ✓     |     ✓     |     ✘     |       ✘       |
| configmaps       |     ✓     |     ✓     |     ✓     |       ✘       |
| PVC              |     ✓     |     ✓     |     ✘     |       ✘       |
| PV               |     ✓     |     ✓     |     ✘     |       ✘       |
| Namespace        |     ✓     |     ✘     |     ✘     |       ✓       |


### User Management Models
The K8s IAM Operator supports two primary user management models: Centralized and Decentralized.

1. Centralized User Management: In this model, all users are created in a single namespace, typically iam. This approach facilitates centralized management of user access and roles.

2. Decentralized User Management: Alternatively, in a decentralized model, each user has a separate namespace. This approach allows for more granular control over access and resources, with each user's service account and configuration file managed within their dedicated namespace.


### UseCase 1: Centralized User Management with K8s IAM Operator

#### Scenario Overview:
In a centralized user management model, the K8s IAM Operator is used to manage all users within a single, dedicated namespace, typically named `iam`. This approach simplifies the oversight of user access and role assignments across the Kubernetes environment.

#### Step-by-Step Implementation:

1. **Preparation**: Ensure the K8s IAM Operator is deployed and operational in your Kubernetes cluster.

2. **Define Roles and Permissions**:
   - Establish the roles and permissions required for your organization in the `iam` namespace. This could include roles like `admin`, `developer`, `observer`, etc., each with specific permissions as defined in your permissions matrix.

3. **User Creation**:
   - Create users as ServiceAccounts in the `iam` namespace. 
   - Each user will have roles and permissions assigned based on organizational requirements.

    Example for creating a user named `alice` with an `observer` role:
    ```kubernetes
    apiVersion: k8sio.auth/v1
    kind: User
    metadata:
      name: tom
      namespace: iam
    spec:
      enabled: true
      CRoles:
      - namespace: tom
        clusterRole: observer
		group: devops
    ```

4. **Access Management**:
   - Manage user access by assigning or modifying the roles in the `iam` namespace.
   - Update or revoke roles as needed to reflect changes in user responsibilities or employment status.

5. **Monitoring and Auditing**:
   - Regularly monitor and audit user activities and role assignments to ensure compliance with organizational policies.
   - Use the K8s IAM Operator's features to track and log user actions for security and compliance purposes.

### Benefits of Centralized User Management
- **Simplified Oversight**: Centralizes user management, making it easier to oversee and update user roles and permissions.
- **Enhanced Security**: Allows for consistent application of security policies across all users.
- **Efficient User Administration**: Streamlines the process of adding, removing, or changing user roles and access rights.


The following actions have been performed when created user:

- Created a user named "tom" as a ServiceAccount in the "iam" namespace.
- If enabled is true, we will generate a kubeconfig for remote access.
- Created a namespace named "tom" specifically for user "tom".
- User 'tom' has been granted observer permissions for the 'tom' namespace.
- Generated a kubeconfig file for user "tom".
- Saved the kubeconfig file in a secret within the "tom" namespace.


### UseCase 2: Decentralized User Management with K8s IAM Operator

### Scenario Overview
In a decentralized user management model, the K8s IAM Operator manages users in individual namespaces, providing granular control over access and resources. Each user has their own namespace, service account, and configuration, ensuring tailored access and role management.

### Step-by-Step Implementation

1. **Preparation**: Ensure the K8s IAM Operator is deployed and operational in your Kubernetes cluster.

2. **Namespace Creation for Each User**:
   - Create a separate namespace for each user, named after the user for easy identification.
   - Example for a user named `bob`:
     ```shell
     kubectl create namespace bob
     ```

3. **Define Roles and Permissions for Each Namespace**:
   - Define the roles and permissions specific to each user within their namespace.
   - This allows for custom role configurations catering to the specific needs or responsibilities of each user.

4. **User Creation and Role Assignment**:
   - Create a ServiceAccount for each user in their respective namespace and assign the appropriate roles.
   
    Example for creating a user `bob` in his namespace with a `developer` role:
    ```kubernetes
	apiVersion: k8sio.auth/v1
	kind: Role
	metadata:
  	  namespace: bob
  	  name: developer
	spec:
  	  rules:
        - apiGroups:
           - ""
          resources:
        	- pods
        	- services
          verbs:
        	- get
        	- list
        	- watch
            - create
            - update
            - delete

	```
	```kubernetes
    apiVersion: k8sio.auth/v1
    kind: User
    metadata:
      name: bob
      namespace: bob
    spec:
      enabled: true
      Roles:
      - developer
    ```

5. **Access Management and Configuration**:
   - Manage each user's access by customizing their roles and permissions within their namespace.
   - Provide each user with a kubeconfig file, granting access to their namespace.

6. **Regular Monitoring and Updates**:
   - Monitor each namespace for user activities and compliance with organizational policies.
   - Update roles and permissions as the user’s responsibilities evolve or as project requirements change.

### Benefits of Decentralized User Management
- **Granular Control**: Offers fine-grained control over access and resources on a per-user basis.
- **Enhanced Security and Privacy**: Limits the scope of access, reducing the risk of unauthorized access to sensitive resources.
- **Customized Environment for Each User**: Allows users to have a tailored environment that suits their specific needs and roles.


### General Consideration:
Before creating users, verify that the cluster role you want to use exists, otherwise create it beforehand. Be aware that the Role in Kubernetes is a Namespaced resource, which must be in the same namespace to be assigned, otherwise, it will have no effect. The use of a group is not mandatory, it is used for managing permissions by group, which means that even if it is not defined, the user will still be created.
