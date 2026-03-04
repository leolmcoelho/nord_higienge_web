/** Cliente Socket.IO */
class SocketManager {
    constructor() {
        this.socket = null;
        this.jobCallbacks = new Map();
    }

    connect() {
        this.socket = io({
            transports: ['websocket', 'polling']
        });

        this.socket.on('connect', () => {
            console.log('Conectado ao Socket.IO');
        });

        this.socket.on('disconnect', () => {
            console.log('Desconectado do Socket.IO');
        });

        this.socket.on('connected', (data) => {
            console.log('Mensagem do servidor:', data.message);
        });

        this.socket.on('job_progress', (data) => {
            this.handleJobProgress(data);
        });

        this.socket.on('job_completed', (data) => {
            this.handleJobCompleted(data);
        });

        this.socket.on('job_failed', (data) => {
            this.handleJobFailed(data);
        });

        this.socket.on('job_status_update', (data) => {
            this.handleJobStatusUpdate(data);
        });
    }

    joinJob(jobUuid) {
        if (this.socket) {
            this.socket.emit('join_job', {job_uuid: jobUuid});
        }
    }

    leaveJob(jobUuid) {
        if (this.socket) {
            this.socket.emit('leave_job', {job_uuid: jobUuid});
        }
    }

    onJobProgress(callback) {
        this.jobCallbacks.set('progress', callback);
    }

    onJobCompleted(callback) {
        this.jobCallbacks.set('completed', callback);
    }

    onJobFailed(callback) {
        this.jobCallbacks.set('failed', callback);
    }

    handleJobProgress(data) {
        const callback = this.jobCallbacks.get('progress');
        if (callback) callback(data);
    }

    handleJobCompleted(data) {
        const callback = this.jobCallbacks.get('completed');
        if (callback) callback(data);
    }

    handleJobFailed(data) {
        const callback = this.jobCallbacks.get('failed');
        if (callback) callback(data);
    }

    handleJobStatusUpdate(data) {
        // Pode ser usado para atualizar status de jobs
        console.log('Status atualizado:', data);
    }
}

// Instância global do Socket.IO
const socketManager = new SocketManager();
