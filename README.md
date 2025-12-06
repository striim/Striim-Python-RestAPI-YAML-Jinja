# Striim-Python-RestAPI-YAML-Jinja
Python Rest API and Tungsten API samples with YAML configuration files and Jinja rendering

To use StriimAPI.py, in your python virtual environme, please install the requirements by running the following command:

Step 1: pip install -r requirements.txt

Step 2: update striim url, password and username in the file striim_config.yaml

Here are some of the sample commands you can run where StriimAPI.py is located:

    ## example call to list all the applications
    python3 StriimAPI.py -l

    ## example call for fetching a template json based on source and target adapters
    python3 StriimAPI.py -gt '{"sourceAdapter":"OracleReader", "targetAdapter": "SpannerWriter", "applicationName":"app_oracle_spanner_cdc"}'

    ## example call to create an application using template json file 
    python3 StriimAPI.py -ca template.json

    ## example call for deploying an existing application 
    python3 StriimAPI.py -d --app_name 'HomeDepot.app_cdc_pos_training_data' --deployment_options '{"deploymentGroupName": "default","deploymentType": "ANY", "flows": [ {"flowName": "HomeDepot.app_cdc_pos_training_data_SourceFlow","deploymentGroupName": "default","deploymentType": "ANY"}]}'

    ## example call to list the objects in Striim
    python3 StriimAPI.py -rt list_objects.tql

    ## example call to start an application
    python3 StriimAPI.py --start_app --app_name 'databricks_test.app_test_automated_pipeline_databricks'

    ## example call to start IL applications and chain them 
    python3 StriimAPI.py -rt start_chained_apps.tql

    ## example call to get template for Initial Load application from PostgreSQL to Snowflake
    python3 StriimAPI.py -gt '{"sourceAdapter":"DatabaseReader", "targetAdapter": "SnowflakeWriter", "applicationName":"app_postgresql_snowflake_writer_il"}'
