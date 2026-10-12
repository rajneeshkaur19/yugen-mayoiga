from collections import deque
class StoryGraph:
    def __init__(self):
        self.graph = {}
    def add_scene(self,scene_id):
        if scene_id not in self.graph:
            self.graph[scene_id] = []

    def add_choice(self, from_scene, to_scene):
        self.add_scene(from_scene)
        self.add_scene(to_scene)

        self.graph[from_scene].append(to_scene)

    def get_choices(self, scene_id):
        return self.graph.get(scene_id, [])

    def bfs_shortest_distance(self,start_scene, target_scene):
        queue = deque([(start_scene,0)])
        visited = {start_scene}

        while queue:
            current_scene, distance = queue.popleft()

            if current_scene == target_scene:
                return distance
            for next_scene in self.graph.get(current_scene,[]):
                if next_scene not in visited:
                    visited.add(next_scene)
                    queue.append((next_scene, distance + 1))

        return -1

    def dfs_traversal(self,start_scene):
        visited = set()
        traversal_order = []

        def dfs(scene):
            visited.add(scene)
            traversal_order.append(scene)

            for next_scene in self.graph.get(scene,[]):
                if next_scene not in visited:
                    dfs(next_scene)
        if start_scene in self.graph:
            dfs(start_scene)
        return traversal_order
    def display_graph(self):
        for scene, choices in self.graph.items():
            print(f"{scene}  → {choices}")

if __name__ == "__main__":
    story = StoryGraph()

    story.add_choice("START","HOUSE")
    story.add_choice("START","LEAVE")
    story.add_choice("HOUSE","HALL")
    story.add_choice("HALL","GARDEN")
    story.add_choice("HALL","BASEMENT")
    story.add_choice("BASEMENT","ENDING")

    story.display_graph()

    print("Distance from START to ENDING:", story.bfs_shortest_distance("START","ENDING"))
    print("DFS Traversal:", story.dfs_traversal("START"))
    print("DFS from HOUSE:", story.dfs_traversal("HOUSE"))
    print("DFS from UNKNOWN:", story.dfs_traversal("UNKNOWN"))
        
