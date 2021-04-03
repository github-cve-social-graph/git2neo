import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

import pandas as pd
from py2neo import Graph, Node, Relationship

import private_config
import config
from utils import git_to_neo_queries, git_queries, neo_queries



if __name__ == '__main__':
    NUM_OF_CVE_REPOS_TO_CRAWL = 10
    run_first_time = False


    my_graph = Graph(config.neo4j['endpoint'], name=config.neo4j['db_name'], user=config.neo4j['user_name'], password=config.neo4j['password'])
    if (run_first_time):
        my_graph.delete_all()
        # # Uncomment when refreshing database constraints
        # my_graph.schema.create_uniqueness_constraint('Repo', 'name')
        # my_graph.schema.create_uniqueness_constraint('Person', 'username')

    my_token = private_config.github_token

    #Query repos and stargazers:
    repo= {'Owner': 'torvalds', 'Repo': 'linux'}
    git_to_neo_queries.query_stargazers_by_repo(my_graph, repo, my_token, 1, repo_layer="0")

    users = neo_queries.query_all_usernames(my_graph)
    git_to_neo_queries.query_users_relationships(my_graph, users, my_token)

