app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersecretkey")

# Register Admin Blueprint
from admin_routes import admin_bp
app.register_blueprint(admin_bp)



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.form.get('user_input', '')
    dev_settings = {} 
    
    if not user_input:
        return jsonify({'error': 'Empty message'}), 400

    # Get chat history safely
    chat_history = session.get('chat_history', [])
    
    # Define generator for streaming
    def generate():
        start_time = time.time()
        
        # Yield initial thinking state
        yield json.dumps({"type": "log", "content": "Thinking..."}) + "\n"
        
        full_answer = ""
        sources = []
        needs_email_support = False
        
        # Stream events from the bot
        for event in ask_bot_stream(user_input, chat_history, dev_settings):
            yield json.dumps(event) + "\n"
            
            if event['type'] == 'answer':
                full_answer = event['content']
                needs_email_support = event.get('needs_email_support', False)
                sources = event.get('sources', [])

        end_time = time.time()
        duration = round(end_time - start_time, 2)

        # Log query for analytics
        try:
            query_log_file = 'query_log.json'
            if os.path.exists(query_log_file):
                with open(query_log_file, 'r') as f:
                    try:
                        queries = json.load(f)
                    except json.JSONDecodeError:
                        queries = []
            else:
                queries = []
                
            queries.append({
                "timestamp": datetime.now().isoformat(),
                "query": user_input,
                "response_time": duration
            })
            
            with open(query_log_file, 'w') as f:
                json.dump(queries, f, indent=4)
        except Exception as e:
            print(f"Failed to log query: {e}")

    # Save user message to history
    chat_history.append({'role': 'user', 'content': user_input})
    session['chat_history'] = chat_history
    session.modified = True

    return Response(stream_with_context(generate()), mimetype='application/x-ndjson')

@app.route('/reset', methods=['POST'])
def reset():
    session.clear()
    return jsonify({'status': 'ok'})

@app.route('/summarize', methods=['POST'])
def summarize():
    history = request.json.get('history', [])
    from service_desk_bot import summarize_conversation
    summary = summarize_conversation(history)
    return jsonify({'summary': summary})

@app.route(POLLING_ENDPOINT)
def healthcheck():
    return 'OK', 200

# Serve local PDFs from the 'data/decrypted' directory
@app.route('/files/<path:filename>')
def serve_file(filename):
    # Ensure we are serving from the 'data/decrypted' folder
    file_dir = os.path.join(app.root_path, 'data', 'decrypted')
    return send_from_directory(file_dir, filename)

@app.route('/feedback', methods=['POST'])
def feedback():
    try:
        data = request.json
        feedback_entry = {
            "timestamp": datetime.now().isoformat(),
            "message_id": data.get('message_id'),
            "user_query": data.get('user_query'),
            "bot_response": data.get('bot_response'),
            "sources": data.get('sources', []),
            "rating": data.get('rating'), # 1 for up, -1 for down
            "comment": data.get('comment', '')
        }
        
        log_file = 'feedback_log.json'
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                try:
                    logs = json.load(f)
                except json.JSONDecodeError:
                    logs = []
        else:
            logs = []
            
        logs.append(feedback_entry)
        
        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=4)
            
        return jsonify({"status": "success", "message": "Feedback received"})
    except Exception as e:
        print(f"Feedback error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

APP_FEEDBACK_FILE = 'app_feedback.json'

@app.route('/submit_app_feedback', methods=['POST'])
def submit_app_feedback():
    try:
        data = request.json
        record = {
            "id": int(datetime.now().timestamp() * 1000), # Simple unique ID
            "timestamp": datetime.now().isoformat(),
            "rating": data.get('rating'),
            "comment": data.get('comment')
        }
        
        if os.path.exists(APP_FEEDBACK_FILE):
            try:
                with open(APP_FEEDBACK_FILE, 'r') as f:
                    feedback_data = json.load(f)
            except json.JSONDecodeError:
                feedback_data = []
        else:
            feedback_data = []
            
        feedback_data.append(record)
        
        with open(APP_FEEDBACK_FILE, 'w') as f:
            json.dump(feedback_data, f, indent=4)
            
        return jsonify({"status": "success", "message": "Feedback submitted"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=READONLY_PORT, debug=False)
