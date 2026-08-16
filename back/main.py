import networkx as nx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CourseLoad(BaseModel):
    batch: str
    course: str
    prof: str
    credit: int


class TimetableRequest(BaseModel):
    course_loads: list[CourseLoad]
    days: list[str]
    slots: list[str]
    rooms_available: int


def build_conflict_graph(sessions: list[dict]) -> nx.Graph:
    G = nx.Graph()

    for sess in sessions:
        G.add_node(
            sess["id"],
            batch=sess["batch"],
            course=sess["course"],
            prof=sess["prof"],
        )

    node_list = list(G.nodes(data=True))
    for i in range(len(node_list)):
        for j in range(i + 1, len(node_list)):
            n1, d1 = node_list[i]
            n2, d2 = node_list[j]

            # Conflict if same batch or same professor
            if d1["batch"] == d2["batch"] or d1["prof"] == d2["prof"]:
                G.add_edge(n1, n2)

    return G


@app.post("/generate_timetable")
def generate_timetable(req: TimetableRequest):
    # 1. Build session nodes
    sessions = []
    for cl in req.course_loads:
        for i in range(cl.credit):
            sessions.append(
                {
                    "id": f"{cl.course}_{cl.batch}_L{i+1}",
                    "batch": cl.batch,
                    "course": cl.course,
                    "prof": cl.prof,
                }
            )

    G = build_conflict_graph(sessions)

    # 2. Pre-generate tuple slots (prevents string split bugs)
    week_slots = [(d, s) for d in req.days for s in req.slots]

    assignments: dict[str, tuple[str, str]] = {}
    slot_counts: dict[tuple[str, str], int] = {}

    # 3. Sort nodes by degree descending (Welsh-Powell heuristic)
    sorted_nodes = sorted(G.nodes(), key=lambda n: G.degree(n), reverse=True)

    unassigned_nodes = []

    for node in sorted_nodes:
        # Collect slots already taken by conflicting neighbors
        neighbor_slots = {
            assignments[neigh] for neigh in G.neighbors(node) if neigh in assignments
        }

        assigned = False
        for slot_tuple in week_slots:
            if (
                slot_tuple not in neighbor_slots
                and slot_counts.get(slot_tuple, 0) < req.rooms_available
            ):
                assignments[node] = slot_tuple
                slot_counts[slot_tuple] = slot_counts.get(slot_tuple, 0) + 1
                assigned = True
                break

        if not assigned:
            unassigned_nodes.append(node)

    # 4. Initialize nested timetable structure
    batch_timetables = {
        batch: {day: {slot: [] for slot in req.slots} for day in req.days}
        for batch in {cl.batch for cl in req.course_loads}
    }

    # 5. Fill timetable
    for node, (day, slot) in assignments.items():
        batch = G.nodes[node]["batch"]
        batch_timetables[batch][day][slot].append(node)

    return {
        "timetable": batch_timetables,
        "unassigned_count": len(unassigned_nodes),
        "unassigned_sessions": unassigned_nodes,
    }