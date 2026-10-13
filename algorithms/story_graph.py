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

    def can_reach_ending(self, start_scene, ending_scene):
        distance = self.bfs_shortest_distance(start_scene, ending_scene)
        return distance != -1

    
    def find_dead_ends(self, ending_scenes):
        dead_ends = []

        for scene_id, next_scenes in self.graph.items():
            if not next_scenes and scene_id not in ending_scenes:
                dead_ends.append(scene_id)

        return dead_ends

    def has_cycle(self):
        visited = set()
        recursion_stack = set()

        def dfs(scene_id):
            visited.add(scene_id)
            recursion_stack.add(scene_id)

            for next_scene in self.graph.get(scene_id, []):
                if next_scene not in visited:
                    if dfs(next_scene):
                        return True
                elif next_scene in recursion_stack:
                    return True

            recursion_stack.remove(scene_id)
            return False

        for scene_id in self.graph:
            if scene_id not in visited:
                if dfs(scene_id):
                    return True

        return False

    
    def find_all_paths(self, start_scene, target_scene):
        if start_scene not in self.graph or target_scene not in self.graph:
            return []

        all_paths = []

        def dfs(current_scene, current_path):
            if current_scene == target_scene:
                all_paths.append(current_path.copy())
                return

            for next_scene in self.graph.get(current_scene, []):
                if next_scene not in current_path:
                    current_path.append(next_scene)
                    dfs(next_scene, current_path)
                    current_path.pop()

        dfs(start_scene, [start_scene])
        return all_paths

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
        
