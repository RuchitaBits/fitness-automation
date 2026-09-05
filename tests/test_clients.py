def add_client(client, name="Sam Lee"):
    return client.post("/clients/add", data={"name": name, "age": 30, "height": 175, "weight": 70, "target_weight": 68, "program": "Fat Loss"})


def test_client_creation_retrieval_update_delete(logged_in):
    response = add_client(logged_in)
    assert response.status_code == 302
    page = logged_in.get("/clients")
    assert b"Sam Lee" in page.data
    with logged_in.application.app_context():
        from app import query_db
        client_id = query_db("SELECT id FROM clients", one=True)["id"]
    detail = logged_in.get(f"/clients/{client_id}")
    assert detail.status_code == 200
    logged_in.post(f"/clients/{client_id}/update", data={"weight": 68, "program": "Muscle Gain", "membership_status": "Active"})
    assert b"2380" in logged_in.get(f"/clients/{client_id}").data
    logged_in.post(f"/clients/{client_id}/delete")
    assert b"Sam Lee" not in logged_in.get("/clients").data


def test_invalid_client_input(logged_in):
    add_client(logged_in, name="")
    assert b"No clients yet" in logged_in.get("/clients").data