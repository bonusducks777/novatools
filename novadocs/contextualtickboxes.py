import gradio as gr
import requests
import json
import re
from PyPDF2 import PdfReader
import os
import pickle
import shutil
from datetime import datetime

ollama_server = "http://localhost:11434"  # Default Ollama server address
processed_texts = {}
CHUNK_SIZE = 4000  # Adjust this value based on your model's context window
history = []
current_profile = None
profiles = {}

# Directory to store profiles
PROFILES_DIR = "profiles"

os.makedirs(PROFILES_DIR, exist_ok=True)

def create_default_profile():
    return {
        "pdfs": {},
        "agents": ["General"],
        "decision_mode": "Make Decision",
        "custom_text": "",
        "last_question": "",
        "processed_texts": {},
        "applicable_location": "",
        "applicable_entity": "",
        "use_legal_situational_context": False,
        "use_entity_context": False,
        "use_general_crypto_knowledge": False
    }

def load_profiles():
    global profiles
    profiles = {}  # Reset profiles dictionary
    if not os.path.exists(PROFILES_DIR):
        os.makedirs(PROFILES_DIR)
        print(f"Created profiles directory: {PROFILES_DIR}")
    
    for profile_name in os.listdir(PROFILES_DIR):
        profile_path = os.path.join(PROFILES_DIR, profile_name)
        if os.path.isdir(profile_path):
            profile_data_path = os.path.join(profile_path, "profile_data.pkl")
            if os.path.exists(profile_data_path):
                try:
                    with open(profile_data_path, "rb") as f:
                        profile_data = pickle.load(f)
                        profiles[profile_name] = profile_data
                    
                    # Ensure all required keys exist
                    required_keys = ["pdfs", "agents", "decision_mode", "custom_text", "last_question", "processed_texts", "applicable_location", "applicable_entity", "use_legal_situational_context", "use_entity_context", "use_general_crypto_knowledge"]
                    for key in required_keys:
                        if key not in profiles[profile_name]:
                            profiles[profile_name][key] = {} if key == "pdfs" or key == "processed_texts" else ""
                    
                    # Load PDFs
                    pdf_dir = os.path.join(profile_path, "pdfs")
                    if os.path.exists(pdf_dir):
                        for pdf_name in os.listdir(pdf_dir):
                            pdf_path = os.path.join(pdf_dir, pdf_name)
                            if os.path.exists(pdf_path):
                                with open(pdf_path, "rb") as f:
                                    profiles[profile_name]["pdfs"][pdf_name] = f.read()
                            else:
                                print(f"Warning: PDF file not found: {pdf_path}")
                except Exception as e:
                    print(f"Error loading profile {profile_name}: {str(e)}")
                    profiles[profile_name] = create_default_profile()
            else:
                print(f"Warning: profile data file not found for {profile_name}")
                profiles[profile_name] = create_default_profile()
    
    if not profiles:
        print("No profiles found. Creating a default profile.")
        profiles["Default"] = create_default_profile()
        save_profile("Default")
    
    print(f"Loaded profiles: {list(profiles.keys())}")

def save_profile(profile_name):
    profile_path = os.path.join(PROFILES_DIR, profile_name)
    if not os.path.exists(profile_path):
        os.makedirs(profile_path)
    
    # Save all profile data
    profile_data = {
        "agents": profiles[profile_name]["agents"],
        "decision_mode": profiles[profile_name]["decision_mode"],
        "custom_text": profiles[profile_name]["custom_text"],
        "last_question": profiles[profile_name]["last_question"],
        "processed_texts": profiles[profile_name]["processed_texts"],
        "applicable_location": profiles[profile_name]["applicable_location"],
        "applicable_entity": profiles[profile_name]["applicable_entity"],
        "use_legal_situational_context": profiles[profile_name]["use_legal_situational_context"],
        "use_entity_context": profiles[profile_name]["use_entity_context"],
        "use_general_crypto_knowledge": profiles[profile_name]["use_general_crypto_knowledge"]
    }
    with open(os.path.join(profile_path, "profile_data.pkl"), "wb") as f:
        pickle.dump(profile_data, f)
    
    # Save PDFs
    pdf_dir = os.path.join(profile_path, "pdfs")
    if not os.path.exists(pdf_dir):
        os.makedirs(pdf_dir)
    for pdf_name, pdf_content in profiles[profile_name]["pdfs"].items():
        with open(os.path.join(pdf_dir, pdf_name), "wb") as f:
            f.write(pdf_content)

def create_profile(profile_name):
    global profiles, current_profile
    if profile_name not in profiles:
        profiles[profile_name] = create_default_profile()
        processed_texts = profiles[profile_name]["processed_texts"] #Added line
        save_profile(profile_name)
    current_profile = profile_name
    return gr.update(choices=list(profiles.keys()), value=profile_name), gr.update(value=profile_name)

def delete_profile(profile_name):
    global profiles, current_profile
    if profile_name in profiles:
        del profiles[profile_name]
        profile_path = os.path.join(PROFILES_DIR, profile_name)
        if os.path.exists(profile_path):
            shutil.rmtree(profile_path)
        if current_profile == profile_name:
            current_profile = None
        return gr.update(choices=list(profiles.keys()), value=None), f"Profile {profile_name} deleted successfully."
    return gr.update(), f"Profile {profile_name} not found."

def switch_profile(profile_name):
    global current_profile, processed_texts
    if profile_name not in profiles:
        print(f"Profile {profile_name} not found. Creating a new profile.")
        profiles[profile_name] = create_default_profile()
        save_profile(profile_name)
    
    current_profile = profile_name
    processed_texts = profiles[profile_name].get("processed_texts", {})
    
    return (
        gr.update(value=profiles[profile_name].get("agents", ["General"])),
        gr.update(value=profiles[profile_name].get("decision_mode", "Make Decision")),
        gr.update(value=profiles[profile_name].get("custom_text", "")),
        gr.update(value=profiles[profile_name].get("last_question", "")),
        gr.update(value=profiles[profile_name].get("applicable_location", "")),
        gr.update(value=profiles[profile_name].get("applicable_entity", "")),
        gr.update(value=profiles[profile_name].get("use_legal_situational_context", False)),
        gr.update(value=profiles[profile_name].get("use_entity_context", False)),
        gr.update(value=profiles[profile_name].get("use_general_crypto_knowledge", False)),
        gr.update(value=f"Switched to profile: {profile_name}"),
        gr.update(value=list(profiles[profile_name].get("pdfs", {}).keys())),
        *[gr.update(value="") for _ in range(len(priority_explanations))]  # Clear all output fields
    )

def process_pdfs(pdf_files):
    global processed_texts, profiles, current_profile
    print(f"Current working directory: {os.getcwd()}")
    print(f"Processing PDFs: {[pdf_file.name for pdf_file in pdf_files]}")
    if not pdf_files:
        return "Please upload at least one PDF."
    
    if current_profile is None:
        return "Please select or create a profile before processing PDFs."
    
    try:
        # Check for removed PDFs
        current_pdf_names = set(pdf.name for pdf in pdf_files)
        removed_pdfs = set(profiles[current_profile]["pdfs"].keys()) - current_pdf_names
        for removed_pdf in removed_pdfs:
            del profiles[current_profile]["pdfs"][removed_pdf]
            if removed_pdf in profiles[current_profile]["processed_texts"]:
                del profiles[current_profile]["processed_texts"][removed_pdf]
        
        profiles[current_profile]["processed_texts"].clear()  # Clear existing processed texts
        for pdf_file in pdf_files:
            print(f"Attempting to process file: {pdf_file.name}")
            absolute_path = os.path.abspath(pdf_file.name)
            if not os.path.exists(absolute_path):
                print(f"File not found: {absolute_path}")
                return f"Error: File not found - {absolute_path}"
            try:
                reader = PdfReader(absolute_path)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + " "
                filename = os.path.basename(pdf_file.name)
                labeled_text = f"[PDF: {filename}]\n{text.strip()}\n[End of {filename}]"
                profiles[current_profile]["processed_texts"][filename] = labeled_text
                
                # Save PDF content to profile
                with open(absolute_path, "rb") as f:
                    profiles[current_profile]["pdfs"][filename] = f.read()
            except Exception as e:
                error_message = f"Error processing PDF {pdf_file.name}: {str(e)}\nError type: {type(e).__name__}\nFile path: {absolute_path}"
                print(error_message)
                return error_message
        
        save_profile(current_profile)
        
        total_word_count = sum(len(text.split()) for text in profiles[current_profile]["processed_texts"].values())
        success_message = f"Processed {len(profiles[current_profile]['processed_texts'])} unique PDF(s). Total word count: {total_word_count}. All text has been extracted, labeled, and will be used as context."
        print(success_message)
        return success_message
    except Exception as e:
        return f"An error occurred while processing the PDFs: {str(e)}"

priority_explanations = {
    "Maxed": "Combine all agents and provide a concise summary",
    "MasterAgent": "Combine selected agents and provide a concise summary",
    "General": "Consider all aspects",
    "Human wellbeing": "prioritize a higher quality of life for people in terms of better physical and emotional health, and happiness. Also prioritize having the least amount of people from being ill, injured, hurt or dead",
    "Eco-friendliness": "prioritize well-being of the natural environment in terms of having the least amount of air, land, water and waste pollution, deforestation, greenhouse gas emissions and biodiversity loss",
    "Business growth": "prioritize expanding the business, for example, through serving more customers, or building more international offices",
    "Social": "prioritize social aspects",
    "Rule-breaking and Legality": "prioritize highlighting any rule-breaks or legal issues. are there any regulatory or legal issues commonly associated with something mentioned here?",
    "Danger and threat identification": "analyze potential danger sources contained within, or that come with, any object or procedure mentioned, and flag up harm they can cause. are there any danger/harm sources commonly associated with something mentioned here?",
    "Equality": "prioritize fairness and equal treatment for all individuals regardless of their background, ensuring no discrimination or bias",
    "Education": "prioritize educational aspects, including learning opportunities, curriculum development, and access to quality education",
    "Political aspects": "consider political implications, policies, and governance issues related to the decision or situation"
}

color_schemes = {
    "Maxed": "#FFA500",  # Orange color for Maxed
    "MasterAgent": "#FFD700",  # Gold color for MasterAgent
    "General": "#f0f0f0",
    "Human wellbeing": "#e6f3ff",
    "Eco-friendliness": "#e6fff0",
    "Business growth": "#fff0e6",
    "Social": "#f9e6ff",
    "Rule-breaking and Legality": "#ffe6e6",
    "Danger and threat identification": "#ffcccb",  # Light red for danger
    "Equality": "#e6e6fa",  # Lavender for equality
    "Education": "#E6E6FA",  # Lavender for education
    "Political aspects": "#F0FFF0"  # Honeydew for political aspects
}

def ollama_chat(question, context, priority, decision_mode, custom_text, applicable_location, applicable_entity, use_legal_situational_context, use_entity_context, use_general_crypto_knowledge):
    relevant_context = get_relevant_chunk(question, context)
    priority_instruction = f"Only report on {priority.lower()} considerations ({priority_explanations[priority]}) in your decision-making process. Regardless of what is said later in this prompt, only tell me about {priority.lower()} considerations and no other. If there is no relevant information, or comments you can make with common knowledge relavant to the prompt, just state 'No useful info from PDFs in this answer.'" if priority != "General" else ""

    mode_instruction = ""
    if decision_mode == "Pick out Data":
        mode_instruction = "Help surf these documents for relavant data to the user query."
    elif decision_mode == "Evaluate Project":
        mode_instruction = "Evaluate the given decision/idea/project using the information provided, highlighting any bad ideas and good ideas. do this in a crypto-focused context."
    elif decision_mode == "Help Make a Decision":
        mode_instruction = "Help the user make a decision against the information provided. Double check there is nothing wrong in this decision/idea conflicting with the information provided. Be crypto-relavant and also explain both-sides of the argument."

    legal_situational_context = f"Use information from any crypto-relevant legislation, laws, regulations or policies or information relevant to location {applicable_location} or territory {applicable_location} is within and therefore also has laws, ideas, policies, regulations applying to (e.g. country, and then global law if applicable)." if use_legal_situational_context else ""
    entity_context = f"Use your own information relevant to the entity {applicable_entity} somewhere in your response - show off your knowledge and tie it in somewhere." if use_entity_context else ""
    general_crypto_knowledge = "Consider any applicable projects, information or decisions made from general crypto knowledge that you know about. If analysing a project/product, compare it to another similar product and talk about how successful it was and how it could be learned from." if use_general_crypto_knowledge else ""

    formatted_prompt = f"""Your purpose is to be a crypto-specialised AI that helps either pick out data, summarize, or make decisions using data you're provided with and data you can reasonably infer from own knowledge. {priority_instruction}

Your operating mode: {mode_instruction}
##
{legal_situational_context}
{entity_context}
##
{general_crypto_knowledge}

The context contains text from multiple PDFs, labeled with their filenames when they start and end using square brackets. Ignore all old context or information from pdfs not provided in this whole prompt, they CANNOT be used or mentioned. Use these square bracket labels to specify which PDF you're referring to in your answer. Every time you answer a question, specify whether there was any useful info from a PDF if answering from it. Wherever possible, use context from the PDFs to answer your question and quote relevant sentences. Give your answer within a maximum of 70 words and use bullet points, be concise. Sources and references to regulations, laws, policies etc. are allowed outside of the word limit and are greatly appreciated.

{custom_text}

User-provided context: {relevant_context}

User Input: {question}

Answer:"""

    try:
        response = requests.post(f"{ollama_server}/api/chat", json={
            "model": "llama3.2",
            "messages": [{'role': 'user', 'content': formatted_prompt}]
        }, stream=True)
        response.raise_for_status()
        
        full_response = ""
        for line in response.iter_lines():
            if line:
                json_response = json.loads(line)
                if 'message' in json_response and 'content' in json_response['message']:
                    full_response += json_response['message']['content']
                    yield full_response  # Yield the accumulated response for Gradio to update in real-time
        
        final_answer = re.sub(r'<think>.*?</think>', '', full_response, flags=re.DOTALL).strip()
        # Remove the first line if it starts with "Here" or "Here's"
        final_answer = '\n'.join(line for line in final_answer.split('\n') if not line.strip().lower().startswith(("here", "here's")))
        return final_answer
    except requests.RequestException as e:
        return f"Error communicating with Ollama API: {str(e)}"
    except json.JSONDecodeError as e:
        return f"Error decoding JSON response: {str(e)}"
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"

def get_relevant_chunk(question, context, chunk_size=CHUNK_SIZE):
    words = set(question.lower().split())
    chunks = [context[i:i+chunk_size] for i in range(0, len(context), chunk_size)]
    scores = [sum(1 for word in words if word in chunk.lower()) for chunk in chunks]
    return chunks[scores.index(max(scores))]

def generate_MasterAgent_output(results, agents):
    combined_output = " ".join([f"{priority}: {result}" for priority, result in zip(agents, results) if result != "Not selected"])
    prompt = f"Summarize the following outputs in 200 words or less, removing any repetition and stating which priority contributed to each part: {combined_output}. Use bullet points, be concise and reference sources wherever possible. Don't give me an introduction and get straight to the content. Sources and references to regulations, laws, policies etc. are allowed outside of the word limit and are greatly appreciated."
    
    try:
        response = requests.post(f"{ollama_server}/api/chat", json={
            "model": "llama3.2",
            "messages": [{'role': 'user', 'content': prompt}]
        }, stream=True)
        response.raise_for_status()
        
        full_response = ""
        for line in response.iter_lines():
            if line:
                json_response = json.loads(line)
                if 'message' in json_response and 'content' in json_response['message']:
                    full_response += json_response['message']['content']
        
        # Remove the first line if it starts with "Here" or "Here's"
        full_response = '\n'.join(line for line in full_response.split('\n') if not line.strip().lower().startswith(("here", "here's")))
        return full_response.strip()
    except Exception as e:
        return f"Error generating MasterAgent output: {str(e)}"

def ask_question(question, agents, decision_mode, custom_text, applicable_location, applicable_entity, use_legal_situational_context, use_entity_context, use_general_crypto_knowledge):
    global processed_texts, history, profiles, current_profile
    if not profiles[current_profile]["processed_texts"]:
        return ["Please process PDFs first before asking questions."] * len(priority_explanations)
    try:
        combined_context = "\n\n".join(profiles[current_profile]["processed_texts"].values())
        results = ["Generating..."] * len(priority_explanations)
        priority_list = list(priority_explanations.keys())
        
        # Generate outputs for all agents except MasterAgent and Maxed
        for i, priority in enumerate(priority_list[2:], 2):  # Skip "Maxed" and "MasterAgent" in this loop
            if priority in agents or "Maxed" in agents:
                for partial_result in ollama_chat(question, combined_context, priority, decision_mode, custom_text, applicable_location, applicable_entity, use_legal_situational_context, use_entity_context, use_general_crypto_knowledge):
                    results[i] = partial_result
                    yield results
            else:
                results[i] = "Not selected"
                yield results
        
        # Generate MasterAgent output if selected
        if "MasterAgent" in agents or "Maxed" in agents:
            selected_agents = agents if "MasterAgent" in agents else priority_list[2:]
            MasterAgent_results = [r for i, r in enumerate(results[2:]) if priority_list[i+2] in selected_agents]
            results[1] = generate_MasterAgent_output(MasterAgent_results, selected_agents)
        else:
            results[1] = "Not selected"
        
        # Generate Maxed output if selected
        if "Maxed" in agents:
            results[0] = generate_MasterAgent_output(results[2:], priority_list[2:])
        else:
            results[0] = "Not selected"
        
        yield results
        
        # Save the history and update profile
        history.append({
            "question": question,
            "agents": agents,
            "decision_mode": decision_mode,
            "custom_text": custom_text,
            "applicable_location": applicable_location,
            "applicable_entity": applicable_entity,
            "use_legal_situational_context": use_legal_situational_context,
            "use_entity_context": use_entity_context,
            "use_general_crypto_knowledge": use_general_crypto_knowledge,
            "results": results[0],  # Only save Maxed interpretation
            "pdfs_used": list(profiles[current_profile]["processed_texts"].keys()),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        profiles[current_profile].update({
            "agents": agents,
            "decision_mode": decision_mode,
            "custom_text": custom_text,
            "last_question": question,
            "applicable_location": applicable_location,
            "applicable_entity": applicable_entity,
            "use_legal_situational_context": use_legal_situational_context,
            "use_entity_context": use_entity_context,
            "use_general_crypto_knowledge": use_general_crypto_knowledge
        })
        save_profile(current_profile)
    except Exception as e:
        error_message = f"An error occurred while processing your question: {str(e)}"
        yield [error_message] * len(priority_explanations)

def display_history():
    history_blocks = []
    for i, entry in enumerate(reversed(history), 1):
        block = f"""
        <div style="border: 1px solid #ddd; padding: 10px; margin-bottom: 10px; background-color: #100c0c;">
            <h3 style="margin-top: 0;">Query {len(history) - i + 1}</h3>
            <p><strong>Timestamp:</strong> {entry['timestamp']}</p>
            <p><strong>Question:</strong> {entry['question']}</p>
            <p><strong>agents:</strong> {', '.join(entry['agents'])}</p>
            <p><strong>Decision Mode:</strong> {entry['decision_mode']}</p>
            <p><strong>Custom Text:</strong> {entry['custom_text']}</p>
            <p><strong>Applicable Location:</strong> {entry['applicable_location']}</p>
            <p><strong>Applicable Entity:</strong> {entry['applicable_entity']}</p>
            <p><strong>Use Situational Context:</strong> {entry['use_legal_situational_context']}</p>
            <p><strong>Use Entity Context:</strong> {entry['use_entity_context']}</p>
            <p><strong>Use Precedents for decision-making:</strong> {entry['use_general_crypto_knowledge']}</p>
            <p><strong>Results:</strong></p>
            <div style="background-color: #fff; padding: 10px; border-left: 3px solid #007bff;">
                {entry['results']}
            </div>
            <p><strong>PDFs used:</strong> {', '.join(entry['pdfs_used'])}</p>
        </div>
        """
        history_blocks.append(block)
    return "".join(history_blocks)

def reload_profiles():
    global profiles
    load_profiles()
    return gr.update(choices=list(profiles.keys()))

def initialize_app():
    global profiles, current_profile
    load_profiles()
    if not profiles:
        profiles["Default"] = create_default_profile()
        save_profile("Default")
    current_profile = list(profiles.keys())[0]
    return gr.update(choices=list(profiles.keys()), value=current_profile)

# Load existing profiles
load_profiles()

def save_agents(agents):
    profiles[current_profile]["agents"] = agents
    save_profile(current_profile)
    return gr.update()

def save_decision_mode(decision_mode):
    profiles[current_profile]["decision_mode"] = decision_mode
    save_profile(current_profile)
    return gr.update()

def save_custom_text(custom_text):
    profiles[current_profile]["custom_text"] = custom_text
    save_profile(current_profile)
    return gr.update()

def save_applicable_location(applicable_location):
    profiles[current_profile]["applicable_location"] = applicable_location
    save_profile(current_profile)
    return gr.update()

def save_applicable_entity(applicable_entity):
    profiles[current_profile]["applicable_entity"] = applicable_entity
    save_profile(current_profile)
    return gr.update()

def save_use_legal_situational_context(use_legal_situational_context):
    profiles[current_profile]["use_legal_situational_context"] = use_legal_situational_context
    save_profile(current_profile)
    return gr.update()

def save_use_entity_context(use_entity_context):
    profiles[current_profile]["use_entity_context"] = use_entity_context
    save_profile(current_profile)
    return gr.update()

def save_use_general_crypto_knowledge(use_general_crypto_knowledge):
    profiles[current_profile]["use_general_crypto_knowledge"] = use_general_crypto_knowledge
    save_profile(current_profile)
    return gr.update()


with gr.Blocks(css="""
    .output-textbox textarea {
        background-color: var(--background-color) !important;
        color: black !important;
    }
""") as demo:
    # gr.Markdown("# NovaDocs - Your specialised agentic Crypto-Document AI")
    # gr.Markdown("Summarise, evaluate and surf using vast amounts of data.")
    
    with gr.Row():
        # with gr.Column(scale=1):
        #     profile_select = gr.Dropdown(choices=list(profiles.keys()), label="Select Profile")
        #     new_profile_name = gr.Textbox(label="New Profile Name")
        #     create_profile_btn = gr.Button("Create New Profile")
        #     delete_profile_btn = gr.Button("Delete Profile")
        #     reload_profiles_btn = gr.Button("Reload Profiles")
            
        with gr.Column(scale=3):
            with gr.Tabs() as tabs:
                with gr.TabItem("Profile"):
                    profile_select = gr.Dropdown(choices=list(profiles.keys()), label="Select Profile")
                    new_profile_name = gr.Textbox(label="New Profile Name")
                    create_profile_btn = gr.Button("Create New Profile")
                    delete_profile_btn = gr.Button("Delete Profile")
                    reload_profiles_btn = gr.Button("Reload Profiles")
                with gr.TabItem("Main"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            pdf_files = gr.File(label="Upload PDFs", file_count="multiple")
                            process_button = gr.Button("Process PDFs")
                            
                            agents = gr.CheckboxGroup(
                                list(priority_explanations.keys()),
                                label="Agents (Select multiple)",
                                value=["General"]
                            )
                            decision_mode = gr.Radio(
                                ["Pick out Data", "Evaluate Project", "Help Make a Decision"],
                                label="Operating Mode",
                                value="Make Decision"
                            )
                            use_general_crypto_knowledge = gr.Checkbox(label="General Crypto Knowledge")
                            with gr.Row():
                                use_legal_situational_context = gr.Checkbox(label="Enable Legal Situational Context")
                                applicable_location = gr.Textbox(label="Applicable Location")
                            with gr.Row():
                                use_entity_context = gr.Checkbox(label="Enable Entity Context")
                                applicable_entity = gr.Textbox(label="Applicable Entity")
                            custom_text = gr.Textbox(label="Custom Prompt Injection", placeholder="Enter any additional instructions/context for the AI...")
                            question_input = gr.Textbox(label="Query:")
                            submit_button = gr.Button("Submit Query")

                        with gr.Column(scale=1):
                            status_output = gr.Textbox(label="Status/Output")
                            output_texts = []
                            for priority in priority_explanations.keys():
                                output_texts.append(
                                    gr.Textbox(
                                        label=f"Output for {priority}",
                                        visible=(priority == "General"),
                                        elem_classes=f"output-textbox",
                                        elem_id=f"output-{priority.lower().replace(' ', '-')}",
                                    )
                                )

                with gr.TabItem("History"):
                    history_output = gr.HTML(label="Query History")
                    refresh_history_button = gr.Button("Refresh History")

    # Add custom CSS for each priority's background color
    for priority, color in color_schemes.items():
        demo.css += f"""
            #{f"output-{priority.lower().replace(' ', '-')}"} textarea {{
                --background-color: {color};
            }}
        """

    def update_visibility(agents):
        return [gr.update(visible=priority in agents or "Maxed" in agents) for priority in priority_explanations.keys()]

    agents.change(fn=update_visibility, inputs=[agents], outputs=output_texts)

    process_button.click(fn=process_pdfs, inputs=[pdf_files], outputs=[status_output])

    def check_processed_pdfs(question, agents, decision_mode, custom_text, applicable_location, applicable_entity, use_legal_situational_context, use_entity_context, use_general_crypto_knowledge):
        if not profiles[current_profile]["processed_texts"]:
            return [gr.update(value="Please process PDFs first before asking questions.")] + [gr.update()] * len(priority_explanations)
        return [gr.update()] * (len(priority_explanations) + 1)

    submit_button.click(
        fn=check_processed_pdfs,
        inputs=[question_input, agents, decision_mode, custom_text, applicable_location, applicable_entity, use_legal_situational_context, use_entity_context, use_general_crypto_knowledge],
        outputs=[status_output] + output_texts
    ).success(
        fn=ask_question,
        inputs=[question_input, agents, decision_mode, custom_text, applicable_location, applicable_entity, use_legal_situational_context, use_entity_context, use_general_crypto_knowledge],
        outputs=output_texts
    )

    refresh_history_button.click(fn=display_history, outputs=[history_output])

    create_profile_btn.click(
        fn=create_profile,
        inputs=[new_profile_name],
        outputs=[profile_select, new_profile_name]
    )

    delete_profile_btn.click(
        fn=delete_profile,
        inputs=[profile_select],
        outputs=[profile_select, status_output]
    )

    reload_profiles_btn.click(fn=reload_profiles, outputs=[profile_select])

    profile_select.change(
        fn=switch_profile,
        inputs=[profile_select],
        outputs=[agents, decision_mode, custom_text, question_input, applicable_location, applicable_entity, use_legal_situational_context, use_entity_context, use_general_crypto_knowledge, status_output, pdf_files] + output_texts
    )

    def update_agents(agents):
        if "Maxed" in agents:
            return list(priority_explanations.keys())
        return agents

    agents.change(
        fn=update_agents,
        inputs=[agents],
        outputs=[agents]
    )

    agents.change(fn=save_agents, inputs=[agents], outputs=[])
    decision_mode.change(fn=save_decision_mode, inputs=[decision_mode], outputs=[])
    custom_text.change(fn=save_custom_text, inputs=[custom_text], outputs=[])
    applicable_location.change(fn=save_applicable_location, inputs=[applicable_location], outputs=[])
    applicable_entity.change(fn=save_applicable_entity, inputs=[applicable_entity], outputs=[])
    use_legal_situational_context.change(fn=save_use_legal_situational_context, inputs=[use_legal_situational_context], outputs=[])
    use_entity_context.change(fn=save_use_entity_context, inputs=[use_entity_context], outputs=[])
    use_general_crypto_knowledge.change(fn=save_use_general_crypto_knowledge, inputs=[use_general_crypto_knowledge], outputs=[])

    # Initialize the app
    demo.load(fn=initialize_app, outputs=[profile_select])

if __name__ == "__main__":
    load_profiles()  # Load profiles before launching the app
    demo.queue()
    demo.launch(share=True)

