import json
import uuid

# Configuration
input_file = r"c:\Users\Pradolux\OneDrive\Documentos\GitHub\P&D\ComercialAPP\Arquivos de referencia\Faq Inteligente.json"
output_file = input_file

def migrate_workflow():
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            workflow = json.load(f)
        
        nodes = workflow.get('nodes', [])
        connections = workflow.get('connections', {})
        
        # 1. Find Chat Trigger Node
        trigger_node_index = -1
        trigger_node_name = ""
        webhook_id = str(uuid.uuid4())
        
        for i, node in enumerate(nodes):
            if node.get('type') == '@n8n/n8n-nodes-langchain.chatTrigger':
                trigger_node_index = i
                trigger_node_name = node.get('name')
                webhook_id = node.get('webhookId', webhook_id)
                break
        
        if trigger_node_index != -1:
            print(f"Found Chat Trigger: {trigger_node_name}")
            
            # 2. Create Webhook Node Replacement
            webhook_node = {
                "parameters": {
                    "httpMethod": "POST",
                    "path": "chat",
                    "responseMode": "lastNode", 
                    "options": {}
                },
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 1,
                "position": nodes[trigger_node_index]['position'],
                "id": nodes[trigger_node_index]['id'], 
                "name": "Webhook",
                "webhookId": webhook_id
            }
            
            nodes[trigger_node_index] = webhook_node
            
            if trigger_node_name in connections:
                connections['Webhook'] = connections.pop(trigger_node_name)
                
            print("Replaced Chat Trigger with Webhook.")
        else:
            print("Chat Trigger node not found (or already replaced).")

        # 3. Handle 'Respond to Chat' Nodes
        for node in nodes:
            if node.get('type') == '@n8n/n8n-nodes-langchain.chat':
                original_name = node.get('name')
                print(f"Modifying Chat Response Node: {original_name}")
                
                # Retrieve the original message content (expression or text)
                params = node.get('parameters', {})
                original_msg = params.get('message', '')
                
                # If message is empty, fallback to simple reply pass-through
                if not original_msg:
                    original_msg = "={{ $json.reply }}"
                
                # Convert to Set node
                node['type'] = 'n8n-nodes-base.set'
                node['typeVersion'] = 1
                node['parameters'] = {
                    "values": {
                        "string": [
                            {
                                "name": "reply", # Keep 'reply' key for compatibility
                                "value": original_msg 
                            }
                        ]
                    },
                    "keepOnlySet": True
                }
                
                # Clean up old params
                # (parameters set above overwrites everything, which is correct for Set node)

        workflow['nodes'] = nodes
        workflow['connections'] = connections
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(workflow, f, indent=2, ensure_ascii=False)
            
        print(f"Successfully migrated workflow to {output_file}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    migrate_workflow()
