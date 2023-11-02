function getFormName() {
    return 'form' + Math.round(Math.random() * 100000000);
}

STRIP_COMMENTS = /((\/\/.*$)|(\/\*[\s\S]*?\*\/))/mg;
ARGUMENT_NAMES = /([^\s,]+)/g;

function callFunction(fn, data) {
    const fnStr = fn.toString().replace(STRIP_COMMENTS, '');
    const fnArgs = fnStr.slice(fnStr.indexOf('(')+1, fnStr.indexOf(')')).match(ARGUMENT_NAMES) || [];

    const args = [];
    for (const arg of fnArgs) {
        if (data?.[arg]) {
            args.push(data[arg]);
        } else if (data?.meta?.[arg]) {
            args.push(data.meta[arg]);
        } else {
            args.push(undefined);
        }
    }

    fn.apply(null, args);
}

function functionArgs(fn) {
    const fnStr = fn.toString().replace(STRIP_COMMENTS, '');
    const fnArgs = fnStr.slice(fnStr.indexOf('(')+1, fnStr.indexOf(')')).match(ARGUMENT_NAMES) || [];
}

angular.module('Cleep').component('configItemDesc', {
    template: `
        <div>
            <md-progress-circular
                ng-if="$ctrl.showLoader"
                md-diameter="24px"
                md-mode="indeterminate"
                style="margin: 10px;"
                flex="none"
            ></md-progress-circular>
            <cl-icon ng-if="$ctrl.showIcon" cl-mdi="{{ $ctrl.icon }}" flex="none" style="margin: 10px;" cl-class="{{ $ctrl.clIconClass }}"></cl-icon>
        </div>
        <div layout="column" layout-align="center start">
            <div>{{ $ctrl.clTitle }}</div>
            <div ng-if="$ctrl.clSubtitle" class="md-caption" style="margin-top: 5px;">{{ $ctrl.clSubtitle }}</div>
        </div>
    `,
    bindings: {
        clIcon: '<',
        clIconClass: '<',
        clTitle: '<',
        clSubtitle: '<',
        clLoading: '<?',
    },
    controller: function () {
        const ctrl = this;
        ctrl.showLoader = false;
        ctrl.showIcon = false;

        ctrl.$onInit = function () {
            ctrl.icon = ctrl.clIcon ?? 'chevron-right';
            ctrl.showLoader = ctrl.clLoading ?? false;
            ctrl.showIcon = !ctrl.showLoader;
        };
    },
});

angular.module('Cleep').component('configItemSaveButton', {
    template: `
        <md-button
            ng-if="$ctrl.clBtnClick"
            ng-click="$ctrl.onClick($event)"
            class="{{ $ctrl.color }} {{ $ctrl.style }} cl-button-sm"
            ng-disabled="($ctrl.checkForm && !$ctrl.clFormRef.inputField.$valid) || $ctrl.clBtnDisabled === true"
        >
            <md-tooltip ng-if="$ctrl.clBtnTooltip">{{ $ctrl.clBtnTooltip }}</md-tooltip>
            <cl-icon cl-mdi="{{ $ctrl.icon }}"></cl-icon>
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

        ctrl.$onInit = function () {
            ctrl.color = ctrl.clBtnColor ?? 'md-primary';
            ctrl.style = ctrl.clBtnStyle ?? 'md-raised';
            ctrl.icon = ctrl.clBtnIcon ?? 'content-save';
            ctrl.checkForm = ctrl.clFormRef ?? false;
        };

        ctrl.onClick = ($event) => {
            if (ctrl.clBtnClick) {
                ctrl.clBtnClick({
                    value: ctrl.clModel,
                    meta: ctrl.clMeta,
                    event: $event,
                });
            }
        };
    },
});

angular.module('Cleep').component('configBasic', {
    transclude: true,
    template: function () {
        const formName = getFormName();
        return (`
        <div layout="column" layout-align="start stretch" layout-gt-xs="row" layout-align-gt-xs="start center" id="{{ $ctrl.clId }}" ng-class="$ctrl.class">
            <config-item-desc
                flex layout="row" layout-align="start-center"
                cl-icon="$ctrl.clIcon" cl-icon-class="$ctrl.clIconClass"
                cl-title="$ctrl.clTitle" cl-subtitle="$ctrl.clSubtitle"
                cl-loading="$ctrl.clLoading"
            ></config-item-desc>
            <div ng-if="!$ctrl.noForm" layout="row" layout-align="end center">
                <form name="` + formName + `" style="margin-bottom: 0px;">
                    <div flex="none" layout="row" layout-align="end center">
                        <ng-transclude flex layout="row" layout-align="end center"></ng-transclude>

                        <config-item-save-button
                            cl-btn-icon="$ctrl.clBtnIcon" cl-btn-style="$ctrl.clBtnStyle" cl-btn-color="$ctrl.clBtnColor" cl-btn-click="$ctrl.clClick" cl-btn-tooltip="$ctrl.clBtnTooltip" cl-btn-disabled="$ctrl.clBtnDisabled"
                            cl-model="$ctrl.clModel" cl-meta="$ctrl.clMeta" cl-form-ref="` + formName + `">
                        </config-item-save-button>
                    </div>
                </form>
            </div>
            <div ng-if="$ctrl.noForm" layout="row" layout-align="end center">
                <ng-transclude flex layout="row" layout-align="end center"></ng-transclude>

                <config-item-save-button
                    cl-btn-icon="$ctrl.clBtnIcon" cl-btn-style="$ctrl.clBtnStyle" cl-btn-color="$ctrl.clBtnColor" cl-btn-click="$ctrl.clClick" cl-btn-tooltip="$ctrl.clBtnTooltip" cl-btn-disabled="$ctrl.clBtnDisabled"
                    cl-disabled="$ctrl.clDisabled" cl-model="$ctrl.clModel" cl-meta="$ctrl.clMeta" cl-form-ref="` + formName + `">
                </config-item-save-button>
            </div>
        </div>
        `);
    },
    bindings: {
        clId: '<',
        clTitle: '<',
        clSubtitle: '<',
        clIcon: '<',
        clIconClass: '<',
        clModel: '<',
        clBtnColor: '<',
        clBtnStyle: '<',
        clBtnIcon: '<',
        clBtnTooltip: '<',
        clBtnDisabled: '<',
        clMeta: '<',
        clClick: '<',
        clNoForm: '<?',
        clClass: '@',
        clDisabled: '<',
        clLoading: '<?',
    },
    controller: function () {
        const ctrl = this;
        ctrl.noForm = false;
        ctrl.class = 'config-item';

        ctrl.$onInit = function () {
            ctrl.noForm = !!ctrl.clClick || !!ctrl.clNoForm;
            ctrl.class += ctrl.clClass ? ' ' + ctrl.clClass : '';
        };
    },
});

angular.module('Cleep').component('configButton', {
    template: `
        <div layout="column" layout-align="start stretch" layout-gt-xs="row" layout-align-gt-xs="start center" id="{{ $ctrl.clId }}" class="config-item">
            <config-item-desc
                flex layout="row" layout-align="start-center"
                cl-icon="$ctrl.clIcon" cl-icon-class="$ctrl.clIconClass"
                cl-title="$ctrl.clTitle" cl-subtitle="$ctrl.clSubtitle">
            </config-item-desc>
            <div flex="none" layout="row" layout-align="end center">
                <md-button ng-click="$ctrl.onClick($event)" class="{{ $ctrl.buttonColor }} {{ $ctrl.buttonStyle }}" ng-disabled="$ctrl.clDisabled">
                    <md-tooltip ng-if="$ctrl.clBtnTooltip">{{ $ctrl.clBtnTooltip }}</md-tooltip>
                    <cl-icon ng-if="$ctrl.clBtnIcon" cl-mdi="{{ $ctrl.clBtnIcon }}"></cl-icon>
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
        clIconClass: '@',
        clBtnColor: '@',
        clBtnStyle: '@',
        clBtnIcon: '@',
        clBtnLabel: '@',
        clBtnTooltip: '@',
        clMeta: '<',
        clClick: '&?',
        clDisabled: '<',
    },
    controller: function () {
        const ctrl = this;

        ctrl.$onInit = function () {
            ctrl.buttonColor = ctrl.clBtnColor ?? 'md-primary';
            ctrl.buttonStyle = ctrl.clBtnStyle ?? 'md-raised';
        };

        ctrl.onClick = ($event) => {
            (ctrl.clClick || angular.noop)({ meta: ctrl.clMeta, event: $event });
        };
    },
});

angular.module('Cleep').component('configButtons', {
    template: `
        <div layout="column" layout-align="start stretch" layout-gt-xs="row" layout-align-gt-xs="start center" id="{{ $ctrl.clId }}" class="config-item">
            <config-item-desc
                flex layout="row" layout-align="start-center"
                cl-icon="$ctrl.clIcon" cl-icon-class="$ctrl.clIconClass"
                cl-title="$ctrl.clTitle" cl-subtitle="$ctrl.clSubtitle">
            </config-item-desc>
            <div flex="none" layout="row" layout-align="end center">
                <div ng-if="$ctrl.buttons.length <= $ctrl.limit" ng-repeat="button in $ctrl.buttons track by $index">
                    <md-button ng-click="$ctrl.onClick($event, button)" class="{{ button.color }} {{ button.style }} cl-button-sm" ng-disabled="button.disabled">
                        <md-tooltip ng-if="button.tooltip">{{ button.tooltip }}</md-tooltip>
                        <cl-icon ng-if="button.icon" cl-mdi="{{ button.icon }}"></cl-icon>
                        {{ button.label }}
                    </md-button>
                </div>

                <div ng-if="$ctrl.buttons.length > $ctrl.limit">
                    <md-menu>
                        <md-button class="md-raised md-primary cl-button-sm" ng-click="$ctrl.openMenu($mdMenu, $event)">
                            <md-tooltip>Choose action</md-tooltip>
                            <cl-icon cl-mdi="dots-vertical"></cl-icon>
                        </md-button>
                        <md-menu-content>
                            <md-menu-item ng-repeat="button in $ctrl.buttons track by $index">
                                <md-button ng-click="$ctrl.onClick($event, button)" class="{{ button.color }} {{ button.style }}" ng-disabled="button.disabled">
                                    <cl-icon ng-if="button.icon" cl-mdi="{{ button.icon }}"></cl-icon>
                                    {{ button.label }}
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
        clIconClass: '@',
        clButtons: '<',
        clLimit: '@?',
    },
    controller: function () {
        const ctrl = this;
        ctrl.buttons = [];
        ctrl.limit = 2;

        ctrl.$onInit = function () {
            ctrl.limit = ctrl.clLimit ?? 2;
        };

        ctrl.$onChanges = function (changes) {
            if (changes.clButtons?.currentValue) {
                ctrl.prepareButtons(changes.clButtons.currentValue);
            }
        };

        ctrl.prepareButtons = function (buttons) {
            if (!angular.isArray(buttons)) {
                console.error(
                    "[cleep] ConfigButtons '" +
                        ctrl.clId +
                        "' cl-buttons options must be an array"
                );
            }

            for (const button of buttons) {
                ctrl.buttons.push({
                    color: button.color ?? '',
                    style: button.style ?? (ctrl.collapse ? '' : 'md-raised'),
                    icon: button.icon,
                    label: button.label,
                    click: button.click,
                    meta: button.meta,
                    tooltip: button.tooltip,
                    disabled: button.disabled,
                });
            }
        };

        ctrl.onClick = function ($event, button) {
            if (!button.click || !angular.isFunction(button.click)) {
                console.error(
                    "[cleep] ConfigButtons '" + ctrl.clId + "' button has no click binded"
                );
                return;
            }
            callFunction(button.click, { meta: button.meta, event: $event });
        };

        ctrl.openMenu = function ($mdMenu, ev) {
            originatorEv = ev;
            $mdMenu.open(ev);
        };
    },
});

angular.module('Cleep').component('configSection', {
    template: `
        <div layout="row" layout-align="start center" layout-gt-xs="row" layout-align-gt-xs="start center" id="{{ $ctrl.clId }}" class="config-item config-item-section">
            <div>
                <cl-icon cl-mdi="{{ $ctrl.icon }}"></cl-icon>
            </div>
            <span>{{ $ctrl.clTitle }}</span>
        </div>
    `,
    bindings: {
        clTitle: '@',
        clIcon: '@',
    },
    controller: function () {
        const ctrl = this;
        ctrl.icon = undefined;

        ctrl.$onInit = function () {
            ctrl.icon = ctrl.clIcon ?? 'bookmark-outline';
        };
    },
});

angular.module('Cleep').component('configInfo', {
    template: `
        <div layout="column" layout-align="start stretch" layout-gt-xs="row" layout-align-gt-xs="start center" id="{{ $ctrl.clId }}" class="config-item">
            <config-item-desc
                flex layout="row" layout-align="start-center"
                cl-icon="$ctrl.clIcon" cl-icon-class="$ctrl.clIconClass"
                cl-title="$ctrl.clTitle" cl-subtitle="$ctrl.clSubtitle">
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
        clIconClass: '@',
        clContent: '<',
        clMode: '@',
    },
    controller: function () {
        const ctrl = this;
        ctrl.mode = '';

        ctrl.$onInit = function () {
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

angular.module('Cleep').component('configNumber', {
    template: `
        <config-basic
            cl-id="$ctrl.clId" cl-title="$ctrl.clTitle" cl-subtitle="$ctrl.clSubtitle"
            cl-icon="$ctrl.clIcon" cl-icon-class="$ctrl.clIconClass"
            cl-model="$ctrl.clModel" cl-meta="$ctrl.clMeta" cl-click="$ctrl.clClick" cl-btn-disabled="$ctrl.clDisabled"
            cl-btn-color="$ctrl.clBtnColor" cl-btn-style="$ctrl.clBtnStyle" cl-btn-icon="$ctrl.clBtnIcon" cl-btn-tooltip="$ctrl.clBtnTooltip"
        >
            <md-input-container ng-if="!$ctrl.doNotDisplay" class="config-input-container-no-margin">
                <input
                    ng-required="$ctrl.clRequired" ng-model="$ctrl.clModel" ng-disabled="$ctrl.clDisabled"
                    min="{{ $ctrl.clMin }}" max="{{ $ctrl.clMax }}" name="inputField"
                    type="number" style="width: 80px;" autocomplete="off"
                >
            </md-input-container>
        </config-basic>
    `,
    bindings: {
        clId: '@',
        clTitle: '@',
        clSubtitle: '@',
        clIcon: '@',
        clIconClass: '@',
        clModel: '=',
        clMax: '<',
        clMin: '<',
        clRequired: '<',
        clBtnColor: '@',
        clBtnStyle: '@',
        clBtnIcon: '@',
        clBtnTooltip: '@',
        clMeta: '<',
        clClick: '&?',
        clDisabled: '<?',
    },
    controller: function () {
        const ctrl = this;
        ctrl.doNotDisplay = false;

        ctrl.$onInit = function () {
            if (isNaN(ctrl.clModel)) {
                console.error(
                    "[cleep] ConfigNumber '" + ctrl.clId + "' cl-model must a number"
                );
                ctrl.doNotDisplay = true;
            }
        };
    },
});

angular.module('Cleep').component('configText', {
    template: `
        <config-basic
            cl-id="$ctrl.clId" cl-title="$ctrl.clTitle" cl-subtitle="$ctrl.clSubtitle"
            cl-icon="$ctrl.clIcon" cl-icon-class="$ctrl.clIconClass"
            cl-model="$ctrl.clModel" cl-meta="$ctrl.clMeta" cl-click="$ctrl.clClick" cl-btn-disabled="$ctrl.clDisabled"
            cl-btn-color="$ctrl.clBtnColor" cl-btn-style="$ctrl.clBtnStyle" cl-btn-icon="$ctrl.clBtnIcon" cl-btn-tooltip="$ctrl.clBtnTooltip"
        >
            <md-input-container class="config-input-container-no-margin">
                <input
                    name="inputField" type="{{ $ctrl.inputType }}"
                    ng-required="$ctrl.clRequired" ng-minlength="$ctrl.clMin" ng-maxlength="$ctrl.clMax" ng-disabled="$ctrl.clDisabled"
                    ng-model="$ctrl.clModel" autocomplete="off"
                >
            </md-input-container>
        </config-basic>
    `,
    bindings: {
        clId: '@',
        clTitle: '@',
        clSubtitle: '@',
        clIcon: '@',
        clIconClass: '@',
        clModel: '=',
        clMax: '<',
        clMin: '<',
        clRequired: '<',
        clPassword: '<',
        clBtnColor: '@',
        clBtnStyle: '@',
        clBtnIcon: '@',
        clBtnTooltip: '@',
        clMeta: '<',
        clClick: '&?',
        clDisabled: '<?',
    },
    controller: function () {
        const ctrl = this;

        ctrl.$onInit = function () {
            ctrl.inputType = ctrl.clPassword ?? false ? 'password' : 'text';
        };
    },
});

angular.module('Cleep').component('configSlider', {
    template: `
        <config-basic
            cl-id="$ctrl.clId" cl-title="$ctrl.clTitle" cl-subtitle="$ctrl.clSubtitle"
            cl-icon="$ctrl.clIcon" cl-icon-class="$ctrl.clIconClass"
            cl-model="$ctrl.clModel" cl-meta="$ctrl.clMeta" cl-click="$ctrl.clClick" cl-btn-disabled="$ctrl.clDisabled"
            cl-btn-color="$ctrl.clBtnColor" cl-btn-style="$ctrl.clBtnStyle" cl-btn-icon="$ctrl.clBtnIcon" cl-btn-tooltip="$ctrl.clBtnTooltip"
        >
            <md-slider-container style="padding-right: 8px;">
                <span>{{ $ctrl.clModel }}</span>
                <md-slider
                    name="inputField" md-discrete class="{{ $ctrl.sliderClass }}"
                    min="{{ $ctrl.clMin }}" max="{{ $ctrl.clMax }}" step="{{ $ctrl.inputStep }}"
                    ng-model="$ctrl.clModel" ng-disabled="$ctrl.clDisabled" ng-change="$ctrl.onChange()">
                </md-slider>
            </md-slider-container>
        </config-basic>
    `,
    bindings: {
        clId: '@',
        clTitle: '@',
        clSubtitle: '@',
        clIcon: '@',
        clIconClass: '@',
        clModel: '=',
        clMax: '<',
        clMin: '<',
        clStep: '<',
        clSliderClass: '@',
        clBtnColor: '@',
        clBtnStyle: '@',
        clBtnIcon: '@',
        clBtnTooltip: '@',
        clMeta: '<',
        clClick: '&?',
        clDisabled: '<?',
        clOnChange: '&?',
    },
    controller: function () {
        const ctrl = this;
        ctrl.inputStep = 1;
        ctrl.sliderClass = '';

        ctrl.$onInit = function () {
            ctrl.inputStep = ctrl.clStep ?? 1;
            ctrl.sliderClass = ctrl.clSliderClass ?? 'md-primary';
        };

        ctrl.onChange = function () {
            const data = {
                value: ctrl.clModel,
                meta: ctrl.clMeta
            };
            (ctrl.clOnChange || angular.noop)(data);
        };
    },
});

angular.module('Cleep').component('configCheckbox', {
    template: `
        <config-basic
            cl-id="$ctrl.clId" cl-title="$ctrl.clTitle" cl-subtitle="$ctrl.clSubtitle"
            cl-icon="$ctrl.clIcon" cl-icon-class="$ctrl.clIconClass"
            cl-model="$ctrl.clModel" cl-meta="$ctrl.clMeta" cl-btn-disabled="$ctrl.clDisabled"
            cl-btn-color="$ctrl.clBtnColor" cl-btn-style="$ctrl.clBtnStyle" cl-btn-icon="$ctrl.clBtnIcon" cl-btn-tooltip="$ctrl.clBtnTooltip"
        >
            <md-checkbox ng-change="$ctrl.onClick($event)" ng-model="$ctrl.clModel" ng-disabled="$ctrl.clDisabled">
                {{ $ctrl.clCaption }}
            </md-checkbox>
        </config-basic>
    `,
    bindings: {
        clId: '@',
        clTitle: '@',
        clSubtitle: '@',
        clIcon: '@',
        clIconClass: '@',
        clModel: '=',
        clCaption: '@',
        clSelectedValue: '@',
        clUnselectedValue: '@',
        clMeta: '<',
        clClick: '&?',
        clDisabled: '<?',
    },
    controller: function () {
        const ctrl = this;

        ctrl.$onInit = function() {
            ctrl.noForm = ctrl.clNoForm ?? false;
        };

        ctrl.onClick = ($event) => {
            const data = {
                value: ctrl.clModel ? (ctrl.clSelectedValue || true) : (ctrl.clUnselectedValue || false),
                meta: ctrl.clMeta,
                event: $event,
            };
            (ctrl.clClick || angular.noop)(data);
        };
    },
});

angular.module('Cleep').component('configSwitch', {
    template: `
        <config-basic
            cl-id="$ctrl.clId" cl-title="$ctrl.clTitle" cl-subtitle="$ctrl.clSubtitle"
            cl-icon="$ctrl.clIcon" cl-icon-class="$ctrl.clIconClass"
            cl-model="$ctrl.clModel" cl-meta="$ctrl.clMeta" cl-btn-disabled="$ctrl.clDisabled"
            cl-btn-color="$ctrl.clBtnColor" cl-btn-style="$ctrl.clBtnStyle" cl-btn-icon="$ctrl.clBtnIcon" cl-btn-tooltip="$ctrl.clBtnTooltip"
        >
            <md-switch ng-change="$ctrl.onClick($event)" ng-model="$ctrl.clModel" ng-disabled="$ctrl.clDisabled" style="margin: 8px 0px;">
                {{ $ctrl.clCaption }}
            </md-switch>
        </config-basic>
    `,
    bindings: {
        clId: '@',
        clTitle: '@',
        clSubtitle: '@',
        clIcon: '@',
        clIconClass: '@',
        clModel: '=',
        clCaption: '@',
        clOnValue: '@',
        clOffValue: '@',
        clMeta: '<',
        clClick: '&?',
        clDisabled: '<?',
    },
    controller: function () {
        const ctrl = this;

        ctrl.onClick = ($event) => {
            const data = {
                value: ctrl.clModel ? (ctrl.clOnValue || true) : (ctrl.clOffValue || false),
                meta: ctrl.clMeta,
                event: $event,
            };
            (ctrl.clClick || angular.noop)(data);
        };
    },
});

angular.module('Cleep').component('configSelect', {
    template: `
        <config-basic
            cl-id="$ctrl.clId" cl-title="$ctrl.clTitle" cl-subtitle="$ctrl.clSubtitle"
            cl-icon="$ctrl.clIcon" cl-icon-class="$ctrl.clIconClass"
            cl-model="$ctrl.clModel" cl-meta="$ctrl.clMeta" cl-click="$ctrl.clClick" cl-btn-disabled="$ctrl.clDisabled"
            cl-btn-color="$ctrl.clBtnColor" cl-btn-style="$ctrl.clBtnStyle" cl-btn-icon="$ctrl.clBtnIcon" cl-btn-tooltip="$ctrl.clBtnTooltip"
        >
            <md-input-container class="config-input-container-no-margin">
                <md-select ng-if="$ctrl.isMultiple" name="inputField" multiple ng-required="$ctrl.clRequired" ng-model="$ctrl.clModel" ng-disabled="$ctrl.clDisabled">
                    <md-option ng-repeat="option in $ctrl.options track by $index" ng-value="option.value" ng-disabled="option.disabled">
                        {{ option.label }}
                    </md-option>
                </md-select>
                <md-select ng-if="!$ctrl.isMultiple" name="inputField" ng-required="$ctrl.clRequired" ng-model="$ctrl.clModel" ng-disabled="$ctrl.clDisabled">
                    <md-option ng-repeat="option in $ctrl.options track by $index" ng-value="option.value" ng-disabled="option.disabled">
                        {{ option.label }}
                    </md-option>
                </md-select>
            </md-input-container>
            <md-button ng-if="$ctrl.showSelectAll" class="md-icon-button" ng-click="$ctrl.selectAll()" ng-disabled="$ctrl.clDisabled">
                <cl-icon cl-mdi="check-all"></cl-icon>
                <md-tooltip>Select all</md-tooltip>
            </md-button>
        </config-basic>
    `,
    bindings: {
        clId: '@',
        clTitle: '@',
        clSubtitle: '@',
        clIcon: '@',
        clIconClass: '@',
        clModel: '=',
        clRequired: '<',
        clOptions: '<',
        clBtnColor: '@',
        clBtnStyle: '@',
        clBtnIcon: '@',
        clBtnTooltip: '@',
        clMeta: '<',
        clClick: '&?',
        clDisabled: '<?',
        clNoSelectAll: '<',
    },
    controller: function () {
        const ctrl = this;
        ctrl.options = [];
        ctrl.isMultiple = false;
        ctrl.showSelectAll = false;

        ctrl.$onInit = function () {
            ctrl.isMultiple = angular.isArray(ctrl.clModel);
            ctrl.showSelectAll = ctrl.isMultiple && !(ctrl.clNoSelectAll ?? false);
        };

        ctrl.$onChanges = function (changes) {
            if (changes.clOptions?.currentValue) {
                ctrl.prepareOptions(changes.clOptions.currentValue);
            }
        };

        ctrl.prepareOptions = function (options) {
            const firstOption = options[0];

            if (!angular.isObject(firstOption)) {
                // array of simple values
                for (const option of options) {
                    ctrl.options.push({
                        label: option,
                        value: option,
                        disabled: false,
                    });
                }
            } else {
                // array of object. Assume that it respects awaited format
                for (const option of options) {
                    ctrl.options.push({
                        label: option.label ?? 'No label',
                        value: option.value ?? 'No value',
                        disabled: !!option.disabled,
                    });
                }
            }
        };

        ctrl.selectAll = function () {
            const selectableOptions = ctrl.options.filter((option) => !option.disabled);
            const fill = ctrl.clModel?.length !== selectableOptions.length;
            ctrl.clModel.splice(0, ctrl.clModel.length);
            if (fill) {
                selectableOptions.forEach((option) => ctrl.clModel.push(option.value));
            }
        };
    },
});

angular.module('Cleep').component('configDate', {
    template: `
        <config-basic
            cl-id="$ctrl.clId" cl-title="$ctrl.clTitle" cl-subtitle="$ctrl.clSubtitle"
            cl-icon="$ctrl.clIcon" cl-icon-class="$ctrl.clIconClass"
            cl-model="$ctrl.clModel" cl-meta="$ctrl.clMeta" cl-click="$ctrl.clClick" cl-btn-disabled="$ctrl.clDisabled"
            cl-btn-color="$ctrl.clBtnColor" cl-btn-style="$ctrl.clBtnStyle" cl-btn-icon="$ctrl.clBtnIcon" cl-btn-tooltip="$ctrl.clBtnTooltip"
        >
            <div>
            <md-datepicker
                name="inputField"
                ng-model="$ctrl.clModel" ng-required="$ctrl.clRequired" md-min-date="$ctrl.clMin" md-max-date="$ctrl.clMax"
                md-mode="$ctrl.inMode" md-hide-icons="calendar" ng-disabled="$ctrl.clDisabled">
            </md-datepicker>
            </div>
        </config-basic>
    `,
    bindings: {
        clId: '@',
        clTitle: '@',
        clSubtitle: '@',
        clIcon: '@',
        clIconClass: '@',
        clModel: '=',
        clMax: '<',
        clMin: '<',
        clRequired: '<',
        clBtnColor: '@',
        clBtnStyle: '@',
        clBtnIcon: '@',
        clBtnTooltip: '@',
        clMeta: '<',
        clClick: '&?',
        clDisabled: '<?'
    },
});

angular.module('Cleep').component('configTime', {
    template: `
        <config-basic
            cl-id="$ctrl.clId" cl-title="$ctrl.clTitle" cl-subtitle="$ctrl.clSubtitle"
            cl-icon="$ctrl.clIcon" cl-icon-class="$ctrl.clIconClass"
            cl-model="$ctrl.clModel" cl-meta="$ctrl.clMeta" cl-click="$ctrl.clClick" cl-btn-disabled="$ctrl.clDisabled"
            cl-btn-color="$ctrl.clBtnColor" cl-btn-style="$ctrl.clBtnStyle" cl-btn-icon="$ctrl.clBtnIcon" cl-btn-tooltip="$ctrl.clBtnTooltip"
        >
            <md-input-container class="config-input-container-no-margin">
                <input
                    ng-required="$ctrl.clRequired" ng-model="$ctrl.clModel"
                    ng-min="$ctrl.clMin" ng-max="$ctrl.clMax" name="inputField"
                    type="time" ng-disabled="$ctrl.clDisabled"
                >
            </md-input-container>
        </config-basic>
    `,
    bindings: {
        clId: '@',
        clTitle: '@',
        clSubtitle: '@',
        clIcon: '@',
        clIconClass: '@',
        clModel: '=',
        clMax: '<',
        clMin: '<',
        clRequired: '<',
        clShowSeconds: '<',
        clShowMilliseconds: '<',
        clBtnColor: '@',
        clBtnStyle: '@',
        clBtnIcon: '@',
        clBtnTooltip: '@',
        clMeta: '<',
        clClick: '&?',
        clDisabled: '<?',
    },
    controller: function () {
        const ctrl = this;

        ctrl.$onInit = function () {
            if (!(ctrl.clModel instanceof Date)) {
                console.error(
                    "[cleep] ConfigTime '" +
                        ctrl.clId +
                        "' cl-model must be a Date instance"
                );
            } else {
                // apply date options
                ctrl.clModel.setMilliseconds(ctrl.clShowMilliseconds ?? false);
                ctrl.clModel.setSeconds(
                    (ctrl.clShowSeconds || ctrl.clShowMilliseconds) ?? false
                );
            }
        };
    },
});

angular.module('Cleep').component('configNote', {
    template: `
        <div layout="row" layout-align="start center" id="{{ $ctrl.clId }}" ng-class="$ctrl.class">
            <cl-icon ng-if="$ctrl.clIcon" cl-mdi="{{ $ctrl.clIcon }}" flex="none" style="margin:10px 20px 10px 10px;" cl-class="icon-md {{ $ctrl.clIconClass }}"></cl-icon>
            <div flex layout="column" layout-align="start stretch" ng-bind-html="$ctrl.clNote"></div>
        </div>
    `,
    bindings: {
        clId: '@',
        clIcon: '@',
        clIconClass: '@',
        clNote: '@',
        clType: '@',
    },
    controller: function () {
        const ctrl = this;
        ctrl.types = {
            none: 'config-item config-item-note-none',
            note: 'config-item config-item-note-note',
            info: 'config-item config-item-note-info',
            success: 'config-item config-item-note-success',
            warning: 'config-item config-item-note-warning',
            error: 'config-item config-item-note-error',
        };
        ctrl.class = ctrl.types[0];

        ctrl.$onInit = function () {
            const type = Object.keys(ctrl.types).includes(ctrl.clType)
                ? ctrl.clType
                : 'note';
            ctrl.class = ctrl.types[type];
        };
    },
});

angular.module('Cleep').component('configProgress', {
    template: `
        <config-basic
            cl-id="$ctrl.clId" cl-title="$ctrl.clTitle" cl-subtitle="$ctrl.clSubtitle"
            cl-icon="$ctrl.clIcon" cl-icon-class="$ctrl.clIconClass"
            cl-model="$ctrl.clModel" cl-meta="$ctrl.clMeta" cl-click="$ctrl.clCancel" cl-no-form="true"
            cl-btn-color="$ctrl.clBtnColor" cl-btn-style="$ctrl.clBtnStyle" cl-btn-icon="$ctrl.clBtnIcon" cl-btn-tooltip="$ctrl.clBtnTooltip" cl-btn-disabled="$ctrl.disabled"
        >
            <md-progress-linear flex="50" md-mode="{{ $ctrl.mode }}" value="{{ $ctrl.clModel }}"></md-progress-linear>
        </config-basic>
    `,
    bindings: {
        clId: '@',
        clTitle: '@',
        clSubtitle: '@',
        clIcon: '@',
        clIconClass: '@',
        clModel: '<',
        clInfinite: '<',
        clBtnColor: '@',
        clBtnStyle: '@',
        clBtnIcon: '@',
        clBtnTooltip: '@',
        clMeta: '<',
        clCancel: '&',
    },
    controller: function () {
        const ctrl = this;
        ctrl.disabled = false;

        ctrl.$onInit = function () {
            ctrl.buttonColor = ctrl.clBtnColor ?? 'md-primary';
            ctrl.buttonStyle = ctrl.clBtnStyle ?? 'md-raised';
            ctrl.buttonIcon = ctrl.clBtnIcon ?? 'cancel';
            ctrl.buttonTooltip = ctrl.clBtnTooltip ?? 'cancel';
            ctrl.mode = !!ctrl.clInfinite ? 'indeterminate' : 'determinate';
        };

        ctrl.$onChanges = function (changes) {
            const value = changes.clModel?.currentValue;
            ctrl.disabled = value <= 0 || value >= 100;
        };
    },
});

angular.module('Cleep').component('configChips', {
    template: `
        <config-basic
            cl-id="$ctrl.clId" cl-title="$ctrl.clTitle" cl-subtitle="$ctrl.clSubtitle"
            cl-icon="$ctrl.clIcon" cl-icon-class="$ctrl.clIconClass"
            cl-model="$ctrl.clModel" cl-meta="$ctrl.clMeta" cl-click="$ctrl.clClick" cl-no-form="true"
            cl-btn-color="$ctrl.clBtnColor" cl-btn-style="$ctrl.clBtnStyle" cl-btn-icon="$ctrl.clBtnIcon"
            cl-btn-tooltip="$ctrl.clBtnTooltip"
        >
            <md-chips
                ng-model="$ctrl.clModel" placeholder="{{ $ctrl.placeholder }}"
                readonly="$ctrl.readonly" md-removable="$ctrl.removable">
            </md-chips>
        </config-basic>
    `,
    bindings: {
        clId: '@',
        clTitle: '@',
        clSubtitle: '@',
        clIcon: '@',
        clIconClass: '@',
        clModel: '=',
        clReadonly: '<',
        clRemovable: '<',
        clRequired: '<',
        clPlaceholder: '@',
        clBtnColor: '@',
        clBtnStyle: '@',
        clBtnIcon: '@',
        clBtnTooltip: '@',
        clMeta: '<',
        clClick: '&?',
    },
    controller: function () {
        const ctrl = this;
        ctrl.removable = false;
        ctrl.readonly = true;

        ctrl.$onInit = function () {
            ctrl.required = ctrl.clRequired ?? false;
            ctrl.readonly = ctrl.clReadonly ?? true;
            ctrl.removable = ctrl.clRemovable ?? false;
            ctrl.placeholder = ctrl.clPlaceholder ?? 'Type new entry';
        };
    },
});

angular.module('Cleep').component('configList', {
    template: `
        <config-basic
            ng-if="$ctrl.clItems.length === 0"
            cl-title="$ctrl.empty" cl-icon="'playlist-remove'"
        ></config-basic>
        <config-basic ng-repeat="item in $ctrl.clItems track by $index"
            cl-title="item.title" cl-subtitle="item.subtitle"
            cl-icon="item.icon" cl-icon-class="item.iconClass"
            cl-class="config-list-item" cl-loading="item.loading"
        >
            <md-button
                ng-if="item.clicks.length>0"
                ng-repeat="click in item.clicks track by $index"
                ng-disabled="click.disabled"
                ng-click="$ctrl.onClick($event, click, item, $index)"
                class="md-secondary md-icon-button {{ click.class }}"
            >
                <md-tooltip ng-if="click.tooltip">{{ click.tooltip }}</md-tooltip>
                <cl-icon cl-mdi="{{ click.icon }}"></cl-icon>
            </md-button>
            <md-checkbox ng-if="$ctrl.clSelectable" class="md-secondary" ng-model="$ctrl.selected[$index]" ng-change="$ctrl.onSelect($index)">
                {{ item.label }}
            </md-checkbox>
        </config-basic>
    `,
    bindings: {
        clId: '@',
        clItems: '<',
        clSelectable: '<',
        clOnSelect: '&?',
        clEmpty: '@',
    },
    controller: function () {
        const ctrl = this;
        ctrl.selected = [];

        ctrl.$onInit = function () {
            ctrl.empty = ctrl.clEmpty ?? 'No item in list';
            ctrl.prepareSelected(ctrl.clItems);
        };

        ctrl.$onChanges = function (changes) {
            if (changes.clItems?.currentValue) {
                ctrl.prepareSelected(changes.clItems.currentValue);
            }
        };

        ctrl.prepareSelected = function (items) {
            if (ctrl.clSelectable) {
                ctrl.selected.splice(0, ctrl.selected.length);
                items.forEach((item) => ctrl.selected.push(!!item.selected));
            }
        };

        ctrl.onSelect = (index) => {
            const data = {
                value: ctrl.selected[index],
                current: ctrl.clItems[index],
                selections: ctrl.selected,
                index,
            };
            (ctrl.clOnSelect || angular.noop)(data);
        };

        ctrl.onClick = ($event, click, item, index) => {
            const data = {
                item,
                index,
                meta: click.meta || item.meta || undefined,
                event: $event
            };
            callFunction(click.click || angular.noop, data);
        };
    },
});
