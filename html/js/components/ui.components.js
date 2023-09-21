angular.module('Cleep').component('clIcon', {
    template: `
        <md-icon ng-if="$ctrl.clTooltip" md-font-icon="mdi mdi-{{ $ctrl.clMdi }}" ng-class="$ctrl.clClass">
            <md-tooltip>{{ $ctrl.clTooltip }}</md-tooltip>
        </md-icon>
        <md-icon ng-if="!$ctrl.clTooltip" md-font-icon="mdi mdi-{{ $ctrl.clMdi }}" ng-class="$ctrl.clClass">
        </md-icon>`,
    bindings: {
        clMdi: '@',
        clTooltip: '@',
        clClass: '@'
    },
});
