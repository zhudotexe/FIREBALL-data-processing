import {createRouter, createWebHistory} from 'vue-router';
import Overview from './views/Overview.vue';
import InstanceViewer from './views/InstanceViewer.vue';

const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes: [
        {path: '/', component: Overview},
        {path: '/instances/:instanceId', component: InstanceViewer, props: true},
    ]
});

export default router;
