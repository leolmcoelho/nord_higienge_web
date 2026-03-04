"""Event handlers do Socket.IO."""
from flask_socketio import emit, join_room, leave_room


def register_socket_events(socketio_instance):
    """Registra todos os event handlers do Socket.IO."""

    @socketio_instance.on('connect')
    def handle_connect():
        """Handle client connection."""
        emit('connected', {'message': 'Connected to Nord Higiene Web'})

    @socketio_instance.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection."""
        print('Client disconnected')

    @socketio_instance.on('join_job')
    def handle_join_job(data):
        """Join a job room for updates."""
        job_uuid = data.get('job_uuid')
        if job_uuid:
            join_room(job_uuid)
            emit('joined_job', {'job_uuid': job_uuid})

    @socketio_instance.on('leave_job')
    def handle_leave_job(data):
        """Leave a job room."""
        job_uuid = data.get('job_uuid')
        if job_uuid:
            leave_room(job_uuid)
            emit('left_job', {'job_uuid': job_uuid})

    @socketio_instance.on('request_job_status')
    def handle_request_status(data):
        """Request current job status."""
        from app.services.job_service import JobService
        job_uuid = data.get('job_uuid')
        job_service = JobService()
        job = job_service.get_job(job_uuid)
        if job:
            emit('job_status_update', job.to_dict(), room=job_uuid)
