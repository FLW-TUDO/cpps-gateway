Cyber Physische Produktions Systeme (CPPS)

Der Orderinhalt implemntiert das CPPS Szenario.

Folgende Entitäten werden vertretten und stehen über die jeweiligen Ports zur Verfügung:

       Entität              Port:
    1. agent-gateway        27771
    2. workstation-gateway  27772
    3. employee-gateway     27773
    4. fms                  8760        http://129.217.152.107
    5. picking              27775


FMS:
/fms/api/reserve_task_robot     ->          task_id,

/fms/api/taskrobot/start_time   ->          task_id, robot_id, klt_id, target

/fms/api/pickrobot/offer        ->          id_task=task['id_task'],
                                            klt_id=task['klt_id'],
                                            robot_id=task['robot_id'],
                                            target=task['target'],
                                            desired_availability_date=task['desired_availability_date'],
                                            alpha_time=task['alpha_time'],
                                            alpha_costs=task['alpha_costs']

/fms/api/taskrobot/drive        ->          robot_id, target

/fms/api/pickrobot/drive        ->          robot_id, target

/fms/api/pickrobot/reserve   (require the parameters)