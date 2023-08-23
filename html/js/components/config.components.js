function getFormName() {
    return 'form' + Math.round(Math.random()*100000000);
}

angular
.module('Cleep')
.component('configItemDesc', {
    template: `
        <md-icon ng-if="$ctrl.icon" md-svg-icon="{{ $ctrl.icon }}" flex="none" style="margin:10px;"></md-icon>
        <div layout="column" layout-align="center start">
            <div>{{ $ctrl.clTitle }}</div>
            <div ng-if="$ctrl.clSubtitle" class="md-caption">{{ $ctrl.clSubtitle }}</div>
        </div>
    `,
    bindings: {
        clIcon: '<',
        clTitle: '<',
        clSubtitle: '<',
    },
    controller: function () {
        const ctrl = this;

        ctrl.$onInit = function() {
            ctrl.icon = ctrl.clIcon ?? 'chevron-right';
        };
    },
});

angular
.module('Cleep')
.component('configItemSaveButton', {
    template: `
        <md-button
            ng-if="$ctrl.clBtnClick"
            ng-click="$ctrl.onClick()"
            class="{{ $ctrl.color }} {{ $ctrl.style }} cl-button-sm"
            ng-disabled="($ctrl.checkForm && !$ctrl.clFormRef.inputField.$valid) || $ctrl.clBtnDisabled"
        >
            <md-tooltip ng-if="$ctrl.clBtnTooltip">{{ $ctrl.clBtnTooltip }}</md-tooltip>
            <md-icon md-svg-icon="{{ $ctrl.icon }}"></md-icon>
        </md-button>
    `,
    bindings: {
        clBtnIcon: '<',
        clBtnColor: '<',
        clBtnStyle: '<',
        clBtnClick: '<',
        clBtnTooltip: '<',
        clBtnDisabled: '<',
        clModel: '<',
        clFormRef: '<',
        clMeta: '<',
    },
    controller: function () {
        const ctrl = this;

        ctrl.$onInit = function() {
            ctrl.color = ctrl.clBtnColor ?? 'md-primary';
            ctrl.style = ctrl.clBtnStyle ?? 'md-raised';
            ctrl.icon = ctrl.clBtnIcon ?? 'content-save';
            ctrl.checkForm = ctrl.clFormRef ?? false;
        };

        ctrl.onClick = () => {
            if (ctrl.clBtnClick) {
                ctrl.clBtnClick({
                    meta: ctrl.clMeta,
                    value: ctrl.clModel,
                });
            }
        };
    },
});

angular
.module('Cleep')
.component('configBase', {
    transclude: true,
    template: function() {
        const formName = getFormName();
        return `
        <div layout="column" layout-align="start stretch" layout-gt-xs="row" layout-align-gt-xs="start center" id="{{ $ctrl.clId }}" class="config-item">
            <config-item-desc
                flex layout="row" layout-align="start-center"
                cl-icon="$ctrl.clIcon" cl-title="$ctrl.clTitle" cl-subtitle="$ctrl.clSubtitle">
            </config-item-desc>
            <form ng-if="!$ctrl.noForm" name="`+formName+`">
                <div flex="none" layout="row" layout-align="end center">
                    <ng-transclude flex layout="row" layout-align="end center"></ng-transclude>

                    <config-item-save-button
                        cl-btn-icon="$ctrl.clBtnIcon" cl-btn-style="$ctrl.clBtnStyle" cl-btn-color="$ctrl.clBtnColor" cl-btn-click="$ctrl.clClick" cl-btn-tooltip="$ctrl.clBtnTooltip" cl-btn-disabled="$ctrl.clBtnDisabled"
                        cl-model="$ctrl.clModel" cl-meta="$ctrl.clMeta" cl-form-ref="`+formName+`">
                    </config-item-save-button>
                </div>
            </form>
            <div ng-if="$ctrl.noForm" flex layout="row" layout-align="end center">
                <ng-transclude flex layout="row" layout-align="end center"></ng-transclude>

                <config-item-save-button
                    cl-btn-icon="$ctrl.clBtnIcon" cl-btn-style="$ctrl.clBtnStyle" cl-btn-color="$ctrl.clBtnColor" cl-btn-click="$ctrl.clClick" cl-btn-tooltip="$ctrl.clBtnTooltip" cl-btn-disabled="$ctrl.clBtnDisabled"
                    cl-model="$ctrl.clModel" cl-meta="$ctrl.clMeta" cl-form-ref="`+formName+`">
                </config-item-save-button>
            </div>
        </div>
        `;
    },
    bindings: {
        clId: '<',
        clTitle: '<',
        clSubtitle: '<',
        clIcon: '<',
        clModel: "<",
        clBtnColor: '<',
        clBtnStyle: '<',
        clBtnIcon: '<',
        clBtnTooltip: '<',
        clBtnDisabled: '<',
        clMeta: '<',
        clClick: '<',
        clNoForm: '<',
    },
    controller: function() {
        const ctrl = this;

        ctrl.$onInit = function() {
            ctrl.noForm = ctrl.clNoForm ?? false;
        };
    },
});

angular
.module('Cleep')
.component('configButton', {
    template: `
        <div layout="column" layout-align="start stretch" layout-gt-xs="row" layout-align-gt-xs="start center" id="{{ $ctrl.clId }}" class="config-item">
            <config-item-desc
                flex layout="row" layout-align="start-center"
                cl-icon="$ctrl.clIcon" cl-title="$ctrl.clTitle" cl-subtitle="$ctrl.clSubtitle">
            </config-item-desc>
            <div flex="none" layout="row" layout-align="end center">
                <md-button ng-click="$ctrl.onClick()" class="{{ $ctrl.buttonColor }} {{ $ctrl.buttonStyle }}">
                    <md-tooltip ng-if="$ctrl.clBtnTooltip">{{ $ctrl.clBtnTooltip }}</md-tooltip>
                    <md-icon ng-if="$ctrl.clBtnIcon" md-svg-icon="{{ $ctrl.clBtnIcon }}"></md-icon>
                    {{ $ctrl.clBtnLabel }}
                </md-button>
            </div>
        </div>
    `,
    bindings: {
        clId: '@',
        clTitle: '@',
        clSubtitle: '@',
        clIcon: '@',
        clBtnColor: '@',
        clBtnStyle: '@',
        clBtnIcon: '@',
        clBtnLabel: '@',
        clBtnTooltip: '@',
        clMeta: '<',
        clClick: '<',
    },
    controller: function () {
        const ctrl = this;

        ctrl.$onInit = function() {
            ctrl.buttonColor = ctrl.clBtnColor ?? 'md-primary';
            ctrl.buttonStyle = ctrl.clBtnStyle ?? 'md-raised';
        };

        ctrl.onClick = () => {
            if (ctrl.clClick) {
                ctrl.clClick({ meta: ctrl.clMeta });
            }
        };
    },
});

angular
.module('Cleep')
.component('configButtons', {
    template: `
        <div layout="column" layout-align="start stretch" layout-gt-xs="row" layout-align-gt-xs="start center" id="{{ $ctrl.clId }}" class="config-item">
            <config-item-desc
                flex layout="row" layout-align="start-center"
                cl-icon="$ctrl.clIcon" cl-title="$ctrl.clTitle" cl-subtitle="$ctrl.clSubtitle">
            </config-item-desc>
            <div flex="none" layout="row" layout-align="end center">
                <div ng-if="$ctrl.buttons.length<=$ctrl.limit" ng-repeat="button in $ctrl.buttons">
                    <md-button ng-click="$ctrl.onClick(button)" class="{{ button.color }} {{ button.style }} cl-button-sm">
                        <md-icon ng-if="button.icon" md-svg-icon="{{ button.icon }}"></md-icon>
                        {{ button.label }}
                    </md-button>
                </div>

                <div ng-if="$ctrl.buttons.length>$ctrl.limit">
                    <md-menu>
                        <md-button class="md-raised md-primary cl-button-sm" ng-click="$ctrl.openMenu($mdMenu, $event)">
                            <md-tooltip>Choose action</md-tooltip>
                            <md-icon md-svg-icon="dots-vertical"></md-icon>
                        </md-button>
                        <md-menu-content>
                            <md-menu-item ng-repeat="button in $ctrl.buttons">
                                <md-button ng-click="$ctrl.onClick(button)" class="{{ button.color }} {{ button.style }} cl-button-sm">
                                    <md-tooltip ng-if="button.tooltip">{{ button.tooltip }}</md-tooltip>
                                    <md-icon ng-if="button.icon" md-svg-icon="{{ button.icon }}"></md-icon>
                                    {{ button.label }} {{ button.color }}
                                </md-button>
                            </md-menu-item>
                        </md-menu-content>
                    </md-menu>
                </div>
            </div>
        </div>
    `,
    bindings: {
        clId: '@',
        clTitle: '@',
        clSubtitle: '@',
        clIcon: '@',
        clButtons: '<',
    },
    controller: function () {
        const ctrl = this;
        ctrl.buttons = [];
        ctrl.limit = 2;

        ctrl.$onInit = function() {
            if (!angular.isArray(ctrl.clButtons)) {
                console.error("[cleep] ConfigButtons '"+ctrl.clId+"' cl-buttons options must be an array");
            } else {
                ctrl.prepareButtons(ctrl.clButtons);
            }
        };

        ctrl.prepareButtons = function(buttons) {
            for (const button of buttons) {
                ctrl.buttons.push({
                    color: button.color ?? (buttons.length>ctrl.limit ? '' : 'md-primary'),
                    style: buttons.length>ctrl.limit ? '' : (button.style ?? 'md-raised'),
                    icon: button.icon,
                    label: button.label,
                    click: button.click ?? ctrl.dummyClick,
                    meta: button.meta,
                    tooltip: button.tooltip,
                });
            }
        };

        ctrl.onClick = function(button) {
            if (!button.click) {
                console.warn("[cleep] ConfigButtons '"+ctrl.clId+"' button has no click binded");
                return;
            }
            if (angular.isFunction(button.click)) {
                console.warn("[cleep] ConfigButtons '"+ctrl.clId+"' button must has function binded to click option");
                return;
            }

            button.click({ meta: button.meta });
        };

        ctrl.openMenu = function($mdMenu, ev) {
            originatorEv = ev;
            $mdMenu.open(ev);
        };
    },
});

angular
.module('Cleep')
.component('configSection', {
    template: function() {
        const formName = getFormName();
        return `
        <div layout="column" layout-align="start stretch" layout-gt-xs="row" layout-align-gt-xs="start center" id="{{ $ctrl.clId }}" class="config-item config-item-section">
            <span>{{ $ctrl.clTitle }}</span>
        </div>
        `;
    },
    bindings: {
        clTitle: '@',
    },
    controller: function () { },
});

angular
.module('Cleep')
.component('configInfo', {
    template: `
        <div layout="column" layout-align="start stretch" layout-gt-xs="row" layout-align-gt-xs="start center" id="{{ $ctrl.clId }}" class="config-item">
            <config-item-desc
                flex layout="row" layout-align="start-center"
                cl-icon="$ctrl.clIcon" cl-title="$ctrl.clTitle" cl-subtitle="$ctrl.clSubtitle">
            </config-item-desc>
            <div flex="none" layout="row" layout-align="end center">
                <span ng-if="$ctrl.mode === 'markdown'" marked="$ctrl.clContent"></span>
                <span ng-if="$ctrl.mode === 'html'" ng-bind-html="$ctrl.clContent"></span>
                <span ng-if="$ctrl.mode === ''">{{ $ctrl.clContent }}</span>
            </div>
        </div>
    `,
    bindings: {
        clId: '@',
        clTitle: '@',
        clSubtitle: '@',
        clIcon: '@',
        clContent: '@',
        clMode: '@',
    },
    controller: function () {
        const ctrl = this;
        ctrl.mode = '';

        ctrl.$onInit = function() {
            const mode = ctrl.clMode?.toLowerCase();
            if (mode === 'html') {
                ctrl.mode = 'html';
            } else if (mode === 'markdown') {
                ctrl.mode = 'markdown';
            } else {
                ctrl.mode = '';
            }
        };
    },
});

angular
.module('Cleep')
.component('configNumber', {
    template: `
        <config-base
            cl-id="$ctrl.clId" cl-title="$ctrl.clTitle" cl-Subtitle="$ctrl.clSubtitle" cl-icon="$ctrl.clIcon"
            cl-model="$ctrl.clModel" cl-meta="$ctrl.clMeta" cl-click="$ctrl.clClick"
            cl-btn-color="$ctrl.clBtnColor" cl-btn-style="$ctrl.clBtnStyle" cl-btn-icon="$ctrl.clBtnIcon" cl-btn-tooltip="$ctrl.clBtnTooltip"
        >
            <md-input-container ng-if="!$ctrl.doNotDisplay">
                <input ng-required="$ctrl.clRequired" ng-model="$ctrl.clModel" min="{{ $ctrl.clMin }}" max="{{ $ctrl.clMax }}" name="inputField" type="number" style="width: 80px;">
            </md-input-container>
        </config-base>
    `,
    bindings: {
        clId: '@',
        clTitle: '@',
        clSubtitle: '@',
        clIcon: '@',
        clModel: "=",
        clMax: "<",
        clMin: "<",
        clRequired: "<",
        clBtnColor: '@',
        clBtnStyle: '@',
        clBtnIcon: '@',
        clBtnTooltip: '@',
        clMeta: '<',
        clClick: '<',
    },
    controller: function () {
        const ctrl = this;
        ctrl.doNotDisplay = false;

        ctrl.$onInit = function() {
            if (isNaN(ctrl.clModel)) {
                console.error("[cleep] ConfigNumber '"+ctrl.clId+"' cl-model must a number");
                ctrl.doNotDisplay = true;
            }
        };
    },
});

angular
.module('Cleep')
.component('configText', {
    template: `
        <config-base
            cl-id="$ctrl.clId" cl-title="$ctrl.clTitle" cl-Subtitle="$ctrl.clSubtitle" cl-icon="$ctrl.clIcon"
            cl-model="$ctrl.clModel" cl-meta="$ctrl.clMeta" cl-click="$ctrl.clClick"
            cl-btn-color="$ctrl.clBtnColor" cl-btn-style="$ctrl.clBtnStyle" cl-btn-icon="$ctrl.clBtnIcon" cl-btn-tooltip="$ctrl.clBtnTooltip"
        >
            <md-input-container>
                <input
                    name="inputField" type="{{ $ctrl.inputType }}"
                    ng-required="$ctrl.clRequired" ng-minlength="$ctrl.clMin" ng-maxlength="$ctrl.clMax"
                    ng-model="$ctrl.clModel"
                >
            </md-input-container>
        </config-base>
    `,
    bindings: {
        clId: '@',
        clTitle: '@',
        clSubtitle: '@',
        clIcon: '@',
        clModel: "=",
        clMax: "<",
        clMin: "<",
        clRequired: "<",
        clPassword: "<",
        clBtnColor: '@',
        clBtnStyle: '@',
        clBtnIcon: '@',
        clBtnTooltip: '@',
        clMeta: '<',
        clClick: '<',
    },
    controller: function () {
        const ctrl = this;

        ctrl.$onInit = function() {
            ctrl.inputType = ctrl.clPassword ?? false ? "password" : "text";
        };
    },
});

angular
.module('Cleep')
.component('configSlider', {
    template: `
        <config-base
            cl-id="$ctrl.clId" cl-title="$ctrl.clTitle" cl-Subtitle="$ctrl.clSubtitle" cl-icon="$ctrl.clIcon"
            cl-model="$ctrl.clModel" cl-meta="$ctrl.clMeta" cl-click="$ctrl.clClick"
            cl-btn-color="$ctrl.clBtnColor" cl-btn-style="$ctrl.clBtnStyle" cl-btn-icon="$ctrl.clBtnIcon" cl-btn-tooltip="$ctrl.clBtnTooltip"
        >
            <md-slider-container>
                <span>{{ $ctrl.clModel }}</span>
                <md-slider
                    name="inputField" md-discrete class="{{ $ctrl.clSliderClass }}"
                    min="{{ $ctrl.clMin }}" max="{{ $ctrl.clMax }}" step="{{ $ctrl.inputStep }}"
                    ng-model="$ctrl.clModel">
                </md-slider>
            </md-slider-container>
        </config-base>
    `,
    bindings: {
        clId: '@',
        clTitle: '@',
        clSubtitle: '@',
        clIcon: '@',
        clModel: "=",
        clMax: "<",
        clMin: "<",
        clStep: "<",
        clSliderClass: "@",
        clBtnColor: '@',
        clBtnStyle: '@',
        clBtnIcon: '@',
        clBtnTooltip: '@',
        clMeta: '<',
        clClick: '<',
    },
    controller: function () {
        const ctrl = this;

        ctrl.$onInit = function() {
            ctrl.inputStep = ctrl.clStep ?? 1;
        };
    },
});

angular
.module('Cleep')
.component('configCheckbox', {
    template: `
        <config-base
            cl-id="$ctrl.clId" cl-title="$ctrl.clTitle" cl-Subtitle="$ctrl.clSubtitle" cl-icon="$ctrl.clIcon"
            cl-model="$ctrl.clModel" cl-meta="$ctrl.clMeta" cl-no-form="true"
            cl-btn-color="$ctrl.clBtnColor" cl-btn-style="$ctrl.clBtnStyle" cl-btn-icon="$ctrl.clBtnIcon" cl-btn-tooltip="$ctrl.clBtnTooltip"
        >
            <md-checkbox ng-change="$ctrl.onClick()" ng-model="$ctrl.clModel">
                {{ $ctrl.clCaption }}
            </md-checkbox>
        </config-base>
    `,
    bindings: {
        clId: '@',
        clTitle: '@',
        clSubtitle: '@',
        clIcon: '@',
        clModel: '=',
        clCaption: '@',
        clSelectedValue: '@',
        clUnselectedValue: '@',
        clMeta: '<',
        clClick: '<',
    },
    controller: function () {
        const ctrl = this;

        ctrl.onClick = () => {
            if (ctrl.clClick) {
                const value = ctrl.clModel ? ctrl.clSelectedValue || true : ctrl.clUnselectedValue || false;
                ctrl.clClick({
                    meta: ctrl.clMeta,
                    value,
                });
            }
        };
    },
});

angular
.module('Cleep')
.component('configSwitch', {
    template: `
        <config-base
            cl-id="$ctrl.clId" cl-title="$ctrl.clTitle" cl-Subtitle="$ctrl.clSubtitle" cl-icon="$ctrl.clIcon"
            cl-model="$ctrl.clModel" cl-meta="$ctrl.clMeta" cl-no-form="true"
            cl-btn-color="$ctrl.clBtnColor" cl-btn-style="$ctrl.clBtnStyle" cl-btn-icon="$ctrl.clBtnIcon" cl-btn-tooltip="$ctrl.clBtnTooltip"
        >
            <md-switch ng-change="$ctrl.onClick()" ng-model="$ctrl.clModel">
                {{ $ctrl.clCaption }}
            </md-switch>
        </config-base>
    `,
    bindings: {
        clId: '@',
        clTitle: '@',
        clSubtitle: '@',
        clIcon: '@',
        clModel: '=',
        clCaption: '@',
        clOnValue: '@',
        clOffValue: '@',
        clMeta: '<',
        clClick: '<',
    },
    controller: function () {
        const ctrl = this;

        ctrl.onClick = () => {
            if (ctrl.clClick) {
                const value = ctrl.clModel ? ctrl.clOnValue || true : ctrl.clOffValue || false;
                ctrl.clClick({
                    meta: ctrl.clMeta,
                    value,
                });
            }
        };
    },
});

angular
.module('Cleep')
.component('configSelect', {
    template: `
        <config-base
            cl-id="$ctrl.clId" cl-title="$ctrl.clTitle" cl-Subtitle="$ctrl.clSubtitle" cl-icon="$ctrl.clIcon"
            cl-model="$ctrl.clModel" cl-meta="$ctrl.clMeta" cl-click="$ctrl.clClick"
            cl-btn-color="$ctrl.clBtnColor" cl-btn-style="$ctrl.clBtnStyle" cl-btn-icon="$ctrl.clBtnIcon" cl-btn-tooltip="$ctrl.clBtnTooltip"
        >
            <md-input-container>
                <md-select ng-if="$ctrl.isMultiple" name="inputField" multiple ng-required="$ctrl.clRequired" ng-model="$ctrl.clModel">
                    <md-option ng-repeat="option in $ctrl.options" ng-value="option.value" ng-disabled="option.disabled">
                        {{ option.label }}
                    </md-option>
                </md-select>
                <md-select ng-if="!$ctrl.isMultiple" name="inputField" ng-required="$ctrl.clRequired" ng-model="$ctrl.clModel">
                    <md-option ng-repeat="option in $ctrl.options" ng-value="option.value" ng-disabled="option.disabled">
                        {{ option.label }}
                    </md-option>
                </md-select>
            </md-input-container>
        </config-base>
    `,
    bindings: {
        clId: '@',
        clTitle: '@',
        clSubtitle: '@',
        clIcon: '@',
        clModel: '=',
        clRequired: '<',
        clOptions: '<',
        clBtnColor: '@',
        clBtnStyle: '@',
        clBtnIcon: '@',
        clBtnTooltip: '@',
        clMeta: '<',
        clClick: '<',
    },
    controller: function () {
        const ctrl = this;
        ctrl.options = [];
        ctrl.isMultiple = false;

        ctrl.$onInit = function() {
            ctrl.isMultiple = angular.isArray(ctrl.clModel);
            ctrl.prepareOptions();
        };

        ctrl.prepareOptions = function() {
            const firstOption = ctrl.clOptions[0];

            if (!angular.isObject(firstOption)) {
                // array of simple values
                for (const option of ctrl.clOptions) {
                    ctrl.options.push({
                        label: option,
                        value: option,
                        disabled: false,
                    });
                }
            } else {
                // array of object. Assume that it respects awaited format
                for (const option of ctrl.clOptions) {
                    ctrl.options.push({
                        label: option.label || "No label",
                        value: option.value || "No value",
                        disabled: !!option.disabled,
                    });
                }
            }
        };
    },
});

angular
.module('Cleep')
.component('configDate', {
    template: `
        <config-base
            cl-id="$ctrl.clId" cl-title="$ctrl.clTitle" cl-Subtitle="$ctrl.clSubtitle" cl-icon="$ctrl.clIcon"
            cl-model="$ctrl.clModel" cl-meta="$ctrl.clMeta" cl-click="$ctrl.clClick"
            cl-btn-color="$ctrl.clBtnColor" cl-btn-style="$ctrl.clBtnStyle" cl-btn-icon="$ctrl.clBtnIcon" cl-btn-tooltip="$ctrl.clBtnTooltip"
        >
            <div>
            <md-datepicker
                name="inputField"
                ng-model="$ctrl.clModel" ng-required="$ctrl.clRequired" md-min-date="$ctrl.clMin" md-max-date="$ctrl.clMax"
                md-mode="$ctrl.inMode" md-hide-icons="calendar">
            </md-datepicker>
            </div>
        </config-base>
    `,
    bindings: {
        clId: '@',
        clTitle: '@',
        clSubtitle: '@',
        clIcon: '@',
        clModel: "=",
        clMax: "<",
        clMin: "<",
        clRequired: "<",
        clBtnColor: '@',
        clBtnStyle: '@',
        clBtnIcon: '@',
        clBtnTooltip: '@',
        clMeta: '<',
        clClick: '<',
    },
    controller: function () { },
});

angular
.module('Cleep')
.component('configTime', {
    template: `
        <config-base
            cl-id="$ctrl.clId" cl-title="$ctrl.clTitle" cl-Subtitle="$ctrl.clSubtitle" cl-icon="$ctrl.clIcon"
            cl-model="$ctrl.clModel" cl-meta="$ctrl.clMeta" cl-click="$ctrl.clClick"
            cl-btn-color="$ctrl.clBtnColor" cl-btn-style="$ctrl.clBtnStyle" cl-btn-icon="$ctrl.clBtnIcon" cl-btn-tooltip="$ctrl.clBtnTooltip"
        >
            <md-input-container>
                <input ng-required="$ctrl.clRequired" ng-model="$ctrl.clModel" ng-min="$ctrl.clMin" ng-max="$ctrl.clMax" name="inputField" type="time">
            </md-input-container>
        </config-base>
    `,
    bindings: {
        clId: '@',
        clTitle: '@',
        clSubtitle: '@',
        clIcon: '@',
        clModel: "=",
        clMax: "<",
        clMin: "<",
        clRequired: "<",
        clShowSeconds: "<",
        clShowMilliseconds: "<",
        clBtnColor: '@',
        clBtnStyle: '@',
        clBtnIcon: '@',
        clBtnTooltip: '@',
        clMeta: '<',
        clClick: '<',
    },
    controller: function () {
        const ctrl = this;

        ctrl.$onInit = function() {
            if (!(ctrl.clModel instanceof Date)) {
                console.error("[cleep] ConfigTime '"+ctrl.clId+"' cl-model must be a Date instance");
            } else {
                // apply date options
                ctrl.clModel.setMilliseconds(ctrl.clShowMilliseconds ?? false);
                ctrl.clModel.setSeconds((ctrl.clShowSeconds || ctrl.clShowMilliseconds) ?? false);
            }
        };
    },
});


angular
.module('Cleep')
.component('configNote', {
    template: function() {
        return `
        <div layout="row" layout-align="start center" id="{{ $ctrl.clId }}" ng-class="$ctrl.style">
            <md-icon ng-if="$ctrl.clIcon" md-svg-icon="{{ $ctrl.clIcon }}" flex="none" style="margin:10px 20px 10px 10px;" class="icon-md"></md-icon>
            <div flex layout="column" layout-align="start stretch" ng-bind-html="$ctrl.clNote"></div>
        </div>
        `;
    },
    bindings: {
        clId: '@',
        clIcon: '@',
        clNote: '<',
        clStyle: '@',
    },
    controller: function () {
        const ctrl = this;
        ctrl.styles = {
            none: 'config-item config-item-note-none',
            note: 'config-item config-item-note-note',
            info: 'config-item config-item-note-info',
            success: 'config-item config-item-note-success',
            warning: 'config-item config-item-note-warning',
            error: 'config-item config-item-note-error',
        };

        ctrl.$onInit = function() {
            const style = Object.keys(ctrl.styles).includes(ctrl.clStyle) ? ctrl.clStyle : 'none';
            ctrl.style = ctrl.styles[style];
        };
    },
});

angular
.module('Cleep')
.component('configProgress', {
    template: `
        <config-base
            cl-id="$ctrl.clId" cl-title="$ctrl.clTitle" cl-Subtitle="$ctrl.clSubtitle" cl-icon="$ctrl.clIcon"
            cl-model="$ctrl.clModel" cl-meta="$ctrl.clMeta" cl-click="$ctrl.clClick" cl-no-form="true"
            cl-btn-color="$ctrl.clBtnColor" cl-btn-style="$ctrl.clBtnStyle" cl-btn-icon="$ctrl.clBtnIcon" cl-btn-tooltip="$ctrl.clBtnTooltip" cl-btn-disabled="$ctrl.disabled"
        >
            <md-progress-linear flex="50" md-mode="{{ $ctrl.mode }}" value="{{ $ctrl.clModel }}"></md-progress-linear>
        </config-base>
    `,
    bindings: {
        clId: '@',
        clTitle: '@',
        clSubtitle: '@',
        clIcon: '@',
        clModel: "<",
        clInfinite: "<",
        clBtnColor: '@',
        clBtnStyle: '@',
        clBtnIcon: '@',
        clBtnTooltip: '@',
        clMeta: '<',
        clClick: '<',
    },
    controller: function () {
        const ctrl = this;
        ctrl.disabled = false;

        ctrl.$onInit = function() {
            ctrl.buttonColor = ctrl.clBtnColor ?? 'md-primary';
            ctrl.buttonStyle = ctrl.clBtnStyle ?? 'md-raised';
            ctrl.buttonIcon = ctrl.clBtnIcon ?? 'cancel';
            ctrl.buttonTooltip = ctrl.clBtnTooltip ?? 'cancel';
            ctrl.mode = !!ctrl.clInfinite ? 'indeterminate' : 'determinate';
        };

        ctrl.$onChanges = function(changes) {
            const value = changes.clModel?.currentValue;
            if (value<=0 || value>=100) {
                ctrl.disabled = true;
            }
        };
    },
});

angular
.module('Cleep')
.component('configChips', {
    template: `
        <config-base
            cl-id="$ctrl.clId" cl-title="$ctrl.clTitle" cl-Subtitle="$ctrl.clSubtitle" cl-icon="$ctrl.clIcon"
            cl-model="$ctrl.clModel" cl-meta="$ctrl.clMeta" cl-click="$ctrl.clClick" cl-no-form="true"
            cl-btn-color="$ctrl.clBtnColor" cl-btn-style="$ctrl.clBtnStyle" cl-btn-icon="$ctrl.clBtnIcon" cl-btn-tooltip="$ctrl.clBtnTooltip"
        >
                <md-chips ng-model="$ctrl.clModel" readonly="$ctrl.readonly" md-removable="$ctrl.removable" md-enable-chip-edit="$ctrl.editable">
                </md-chips>
        </config-base>
    `,
    bindings: {
        clId: '@',
        clTitle: '@',
        clSubtitle: '@',
        clIcon: '@',
        clModel: "=",
        clReadonly: "<",
        clRequired: "<",
        clBtnColor: '@',
        clBtnStyle: '@',
        clBtnIcon: '@',
        clBtnTooltip: '@',
        clMeta: '<',
        clClick: '<',
    },
    controller: function () {
        const ctrl = this;

        ctrl.$onInit = function() {
            ctrl.required = ctrl.clRequired ?? false;
            ctrl.readonly = ctrl.clReadonly ?? true;
            ctrl.removable = !ctrl.readonly;
            ctrl.editable = !ctrl.readonly;
        };
    },
});

angular
.module('Cleep')
.component('configList', {
    template: function() {
        return `
        <md-list ng-cloak id="{{ $ctrl.clId }}">
            <data-list-item ng-repeat="item in $ctrl.clItems track by $index">
                <md-subheader ng-if="item.subheader" class="md-no-sticky">
                    {{ item.subheader }}
                </md-subheader>

                <md-divider ng-if="item.divider"></md-divider>

                <md-list-item ng-if="item.label || item.labels" ng-class="{'md-2-line': item.labels.length===2, 'md-3-line': item.labels.length===3}">
                    <md-icon md-svg-icon="{{ item.icon || 'chevron-double-right' }}"></md-icon>

                    <p ng-if="item.label || item.labels.length===1">
                        {{ item.label || item.labels[0] }}
                    </p>
                    <div ng-if="item.labels.length===2" class="md-list-item-text" layout="column">
                        <h3>{{ item.labels[0] }}</h3>
                        <p>{{ item.labels[1] }}</p>
                    </div>
                    <div ng-if="item.labels.length===3" class="md-list-item-text" layout="column">
                        <h3>{{ item.labels[0] }}</h3>
                        <h4>{{ item.labels[1] }}</h4>
                        <p>{{ item.labels[2] }}</p>
                    </div>

                    <md-button ng-if="item.clicks.length>0" ng-repeat="click in item.clicks" ng-click="$ctrl.onClick($event, click, item)" class="md-secondary md-icon-button">
                        <md-tooltip ng-if="click.tooltip">{{ click.tooltip }}</md-tooltip>
                        <md-icon md-svg-icon="{{ click.icon }}"></md-icon>
                    </md-button>
                    <md-checkbox ng-if="$ctrl.clSelectable" class="md-secondary" ng-model="$ctrl.selected[$index]" ng-change="$ctrl.onSelect($event, $index)"></md-checkbox>

                </md-list-item>
            </data-list-item>
        </md-list>
        `;
    },
    bindings: {
        clId: '@',
        clItems: '<',
        clSelectable: '<',
        clOnSelect: '<',
    },
    controller: function () {
        const ctrl = this;
        ctrl.selected = [];

        ctrl.$onInit = function() {
            if (ctrl.clSelectable) {
                for (const item in ctrl.clItems) {
                    ctrl.selected.push(false);
                }
            }
        };

        ctrl.onSelect = (ev, index) => {
            const current = {
                index,
                selected: ctrl.selected[index]
            };
            ctrl.clOnSelect(current, ctrl.selected);
        };

        ctrl.onClick = (ev, click, item) => {
            if (click.click) {
                click.click({ meta: click.meta || item.meta || undefined });
            }
        };
    },
});

