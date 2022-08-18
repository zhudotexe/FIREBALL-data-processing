import {library} from "@fortawesome/fontawesome-svg-core";
import {faAngleLeft, faAngleRight, faSort, faSortDown, faSortUp} from "@fortawesome/free-solid-svg-icons";
import {FontAwesomeIcon} from "@fortawesome/vue-fontawesome";

import 'bulma/bulma.sass';
import {createApp} from 'vue';
import App from './App.vue';
import router from './router';

// ==== fontawesome ====
// regular
library.add(faAngleLeft, faAngleRight, faSort, faSortUp, faSortDown);

const app = createApp(App)
    .use(router)
    .component('font-awesome-icon', FontAwesomeIcon)
    .mount('#app');
