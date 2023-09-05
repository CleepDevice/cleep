angular
.module('Cleep')
.component('widgetBasic', {
    transclude: true,
    template: `
        <md-card class="widget-bg-color" flex="100" style="height:100%; margin:0px;">
            <md-card-header ng-if="$ctrl.clTitle">
                <md-card-avatar ng-if="$ctrl.clIcon">
                    <md-icon class="md-avatar-icon" md-svg-icon="{{ $ctrl.clIcon }}"></md-icon>
                </md-card-avatar>
                <md-card-header-text>
                    <span ng-if="$ctrl.clTitle" class="md-title">{{ $ctrl.clTitle }}</span>
                    <span ng-if="$ctrl.clSubtitle" class="md-subhead">{{ $ctrl.clSubtitle }}</span>
                </md-card-header-text>
            </md-card-header>
            <img ng-if="$ctrl.clImage" ng-src="{{ $ctrl.clImage }}" class="md-card-image">
            <md-card-content layout="column" layout-align="center center" md-colors="{{ $ctrl.contentBgColor }}" style="height:100%;">
                <ng-transclude></ng-transclude>
            </md-card-content>
            <md-card-actions ng-if="$ctrl.hasFooter" layout="row">
                <div layout="row" layout-align="start center" flex>
                    <div ng-repeat="footer in $ctrl.footers" style="margin:5px;">
                        <md-icon ng-if="footer.icon" md-svg-icon="{{ footer.icon }}">
                            <md-tooltip>{{ footer.tooltip }}</md-tooltip>
                        </md-icon>
                        <span ng-if="footer.label" class="{{ footer.class }}" flex="100">{{ footer.label }}</span>
                    </div>
                </div>
                <div ng-if="$ctrl.actions.length>0" layout="row" layout-align="end center" flex hide="" show-gt-xs="">
                    <md-button ng-repeat="action in $ctrl.actions" ng-click="$ctrl.onActionClick($event, action)" class="{{ action.class }} {{ $ctrl.clButtonSm }}">
                        <md-icon ng-if="action.icon" md-svg-icon="{{ action.icon }}"></md-icon>
                        {{ action.label }}
                    </md-button>
                </div>
                <div ng-if="$ctrl.actions.length>0" layout="row" layout-align="end center" flex hide-gt-xs="">
                    <md-button ng-repeat="action in $ctrl.actions" ng-click="$ctrl.onActionClick($event, action)" class="{{ action.class }} cl-button-sm">
                        <md-icon ng-if="action.icon" md-svg-icon="{{ action.icon }}"></md-icon>
                    </md-button>
                </div>
            </md-card-actions>
        </md-card>
    `,
    bindings: {
        clDevice: '<',
        clIcon: '<',
        clTitle: '<',
        clSubtitle: '<',
        clActions: '<',
        clFooters: '<',
        clImage: '<',
    },  
    controller: function() {
        const ctrl = this;
        ctrl.actions = [];
        ctrl.footers = [];
        ctrl.hasFooter = false;
        ctrl.BG_OFF_COLOR = {
            background: "default-primary-300",
        };
        ctrl.BG_ON_COLOR = {
            background: "default-accent-400",
        };
        ctrl.contentBgColor = ctrl.BG_OFF_COLOR;

        ctrl.$onInit = function() {
            ctrl.prepareFooters(ctrl.clFooters);
            ctrl.prepareActions(ctrl.clActions);
        };

        ctrl.$onChanges = function(newVal, oldVal) {
            ctrl.contentBgColor = newVal.clDevice?.on ? ctrl.BG_ON_COLOR : ctrl.BG_OFF_COLOR;
        };

        ctrl.prepareFooters = function(footers) {
            if (!footers?.length) {
                return;
            }
            ctrl.hasFooter = true;

            for (const footer of footers) {
                ctrl.footers.push({
                    icon: footer.icon,
                    tooltip: footer.tooltip,
                    label: footer.label,
                    class: footer.class ?? 'md-caption',
                });
            }
        };

        ctrl.prepareActions = function(actions) {
            if (!actions?.length) {
                return;
            }
            ctrl.hasFooter = true;

            for (const action of actions) {
                ctrl.actions.push({
                    icon: action.icon,
                    label: action.label,
                    click: action.click,
                    class: action.class,
                    clButtonSm: !action.label?.length ? 'cl-button-sm' : '',
                });
            }
        };

        ctrl.onActionClick = (ev, action) => {
            if (action.click) {
                action.click();
            }
        };
    },  
});

