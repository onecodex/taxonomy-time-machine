import { createRouter, createWebHistory } from "vue-router";

const TaxonomyTimeMachine = () =>
  import("../components/TaxonomyTimeMachine.vue");
const BulkNameResolver = () => import("../components/BulkNameResolver.vue");

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "home",
      component: TaxonomyTimeMachine,
    },
    {
      path: "/taxon/:taxId",
      name: "taxon",
      component: TaxonomyTimeMachine,
      props: true,
    },
    {
      path: "/taxon/:taxId/:version",
      name: "taxon-version",
      component: TaxonomyTimeMachine,
      props: true,
    },
    {
      path: "/bulk-resolver",
      name: "bulk-resolver",
      component: BulkNameResolver,
    },
  ],
});

export default router;
