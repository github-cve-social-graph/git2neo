import pandas as pd
from py2neo import Graph, SystemGraph
from py2neo import Node, Relationship

from run_query import run_query


def query_stargazers_from_repos(neo4j_graph, repos_df, git_token, limit_stargazers_per_repo_query):
    headers = {'Authorization': 'token ' + git_token}
    query = """
       query {{
           repository(owner:"{0}", name:"{1}") {{
               stargazers(first:100 {2}) {{
                   pageInfo {{
                       endCursor
                       hasNextPage
                       hasPreviousPage
                       startCursor
                   }}
                   edges {{
                       starredAt
                       node {{
                           login
                           location
                           starredRepositories {{
                               totalCount
                           }}
                       }}
                   }}
               }}
           }}
       }}
       """

    count_repo = 0
    count_error = 0
    error_repos = pd.DataFrame(columns=['Owner', 'Repo'])
    for index in repos_df.index:
        owner = repos_df.loc[index, 'Owner']
        repo = repos_df.loc[index, 'Repo']

        try:
            # Add new repo
            if (len(neo4j_graph.nodes.match("Repo", name=repo)) == 0):
                tx = neo4j_graph.begin()
                new_repo_node = Node("Repo",  name=repo)
                tx.create(new_repo_node)
                tx.commit()
            repo_node = neo4j_graph.nodes.match("Repo", name=repo).first()

            # Query stargazer
            end_cursor = ""  # Start from begining
            count_user = 0
            has_next_page = True
            print(f'Running query for repository "{repo}":')
            while has_next_page and count_user <= limit_stargazers_per_repo_query:  ## LIMIT stargazers
                this_query = query.format(owner, repo, end_cursor)
                result = run_query(this_query, headers)  # Execute the query
                # print(this_query)
                # print(result)
                has_next_page = result['data']['repository']['stargazers']['pageInfo']['hasNextPage']
                end_cursor = result['data']['repository']['stargazers']['pageInfo']['endCursor']
                end_cursor = ', after: "' + end_cursor + '"'
                data = result['data']['repository']['stargazers']['edges']

                users_data = [{
                                'username': item['node']['login'],
                                'location': item['node']['location'],
                                'starred_repo_count': item['node']['starredRepositories']['totalCount']
                             } for item in data]

                tx = neo4j_graph.begin()
                for user in users_data:
                    if (len(neo4j_graph.nodes.match("Person", username=user['username'])) > 0):
                        user_node = neo4j_graph.nodes.match("Person", username=user['username']).first()
                    else:
                        user_node = Node("Person",
                                             username=user['username'],
                                             location=user['location'],
                                             starred_repo_count=user['starred_repo_count']
                                            )
                        tx.create(user_node)

                    user_repo_link = Relationship(user_node, "STARRED", repo_node)
                    tx.create(user_repo_link)
                tx.commit()

                count_user += len(users_data)
                print(str(count_user) + ' users processed.')

            print(f'Repo: "{repo}" done.')
            count_repo += 1
            print(str(count_repo) + ' repos processed.')
            print('')
            print('')

        except Exception as e:
            count_error += 1
            print('Error with repo: ', index, repo)
            print(e)
            print('Number of error so far: ' + str(count_error))
            print('')
            print('')
            error_repos = error_repos.append(repos_df.iloc[[index]])

    error_repos.to_csv("error_repos.csv")


if __name__ == '__main__':
    my_token = ''
    repos_df = pd.read_csv('owner_repo.csv')
    num_of_repos_to_crawl = 5
    sub_repos_df = repos_df.iloc[0:num_of_repos_to_crawl]
    limit_stargazers_per_repo_query = 15000
    run_first_time = False

    my_graph = Graph("bolt://localhost:7687", name="git2neo", user="dat1", password="1")
    if (run_first_time):
        my_graph.delete_all()
        # my_graph.schema.create_uniqueness_constraint('Repo', 'name')
        # my_graph.schema.create_uniqueness_constraint('Person', 'username')

    query_stargazers_from_repos(my_graph, sub_repos_df, my_token, limit_stargazers_per_repo_query)

