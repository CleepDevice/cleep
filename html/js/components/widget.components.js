angular.module('Cleep').component('widgetBasic', {
	transclude: true,
	template: `
        <md-card class="widget-bg-color" flex="100" style="height:100%; margin:0px;">
            <md-card-header ng-if="$ctrl.clTitle">
                <md-card-avatar ng-if="$ctrl.clIcon">
                    <cl-icon class="md-avatar-icon" cl-icon="{{ $ctrl.clIcon }}"></cl-icon>
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
            <md-card-actions ng-if="$ctrl.hasFooter" layout="row" layout-align="space-between center">
                <div ng-repeat="footer in $ctrl.footer" hide="" show-gt-xs="" ng-if="footer.condition($ctrl)">
                    <div ng-if="!footer.click">
                        <cl-icon ng-if="footer.icon" cl-icon="{{ footer.icon }}" cl-tooltip="{{ footer.tooltip }}"></cl-icon>
                        <span ng-if="footer.label" class="{{ footer.class }}" flex="100">{{ footer.label }}</span>
                    </div>
                    <div ng-if="footer.click">
                        <md-button ng-click="$ctrl.onActionClick($event, footer)" class="md-raised {{ footer.class }} {{ $ctrl.clButtonSm }}">
                            <cl-icon ng-if="footer.icon" cl-icon="{{ footer.icon }}"></cl-icon>
                            <md-tooltip ng-if="footer.tooltip">{{ footer.tooltip }}</md-tooltip>
                            {{ footer.label }}
                        </md-button>
                    </div>
                </div>

                <div ng-repeat="footer in $ctrl.footer" hide-gt-xs="" ng-if="footer.condition($ctrl)">
                    <div ng-if="!footer.click">
                        <cl-icon ng-if="footer.icon" cl-icon="{{ footer.icon }}" cl-tooltip="footer.tooltip"></cl-icon>
                        <span ng-if="footer.label" class="{{ footer.class }}" flex="100">{{ footer.label }}</span>
                    </div>
                    <div ng-if="footer.click">
                        <md-button ng-click="$ctrl.onActionClick($event, footer)" class="{{ footer.class }} md-raised cl-button-sm">
                            <cl-icon ng-if="footer.icon" cl-icon="{{ footer.icon }}"></cl-icon>
                            <md-tooltip ng-if="footer.tooltip">{{ footer.tooltip }}</md-tooltip>
                        </md-button>
                    </div>
                </div>
            </md-card-actions>
        </md-card>
    `,
	bindings: {
		clDevice: '<',
		clIcon: '<',
		clTitle: '<',
		clSubtitle: '<',
		clFooter: '<',
		clImage: '<',
	},
	controller: function () {
		const ctrl = this;
		ctrl.footer = [];
		ctrl.hasFooter = false;
		ctrl.BG_OFF_COLOR = {
			background: 'default-primary-300',
		};
		ctrl.BG_ON_COLOR = {
			background: 'default-accent-400',
		};
		ctrl.contentBgColor = ctrl.BG_OFF_COLOR;

		ctrl.$onInit = function () {
			ctrl.prepareFooter(ctrl.clFooter);
		};

		ctrl.$onChanges = function (newVal, oldVal) {
			ctrl.contentBgColor = newVal.clDevice?.on
				? ctrl.BG_ON_COLOR
				: ctrl.BG_OFF_COLOR;
		};

		ctrl.prepareFooter = function (footers) {
			if (!footers?.length) {
				return;
			}
			ctrl.hasFooter = true;

			for (const footer of footers) {
				const isButton = Boolean(footer.click);
				ctrl.footer.push({
					icon: footer.icon,
					tooltip: footer.tooltip ?? undefined,
					label: footer.label,
					class: isButton ? footer.class : footer.class ?? 'md-caption',
					click: isButton ? footer.click : undefined,
					condition: footer.condition,
					clButtonSm: isButton
						? !footer.label?.length
							? 'cl-button-sm'
							: ''
						: undefined,
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

angular.module('Cleep').component('widgetConf', {
	template: `
        <widget-basic
            cl-title="$ctrl.title" cl-subtitle="$ctrl.subtitle" cl-icon="$ctrl.icon"
            cl-image="$ctrl.image" cl-footer="$ctrl.footer" cl-device="$ctrl.clDevice">
            <div ng-bind-html="$ctrl.getContent()"></div>
        </widget-basic>
    `,
	bindings: {
		clDevice: '<',
		clWidgetConf: '<',
		clAppIcon: '@',
	},
	controller: [
		'$interpolate',
		'$scope',
		'cleepService',
		'rpcService',
		'$parse',
		function (
			$interpolate,
			$scope,
			cleepService,
			rpcService,
			$parse
		) {
			const ctrl = this;
			ctrl.icon = undefined;
			ctrl.title = undefined;
			ctrl.subtitle = undefined;
			ctrl.content = undefined;
			ctrl.footer = [];
			ctrl.image = undefined;
			ctrl.deviceRegexp = /device\./g;
			ctrl.commandTo = undefined;

			ctrl.$onInit = function () {
				ctrl.prepareVariables(ctrl.clWidgetConf, ctrl.clAppIcon);
			};

			ctrl.prepareVariables = function (conf, appIcon) {
				(ctrl.icon = conf.header?.icon ?? appIcon),
					(ctrl.title = conf.header?.title ?? ctrl.clDevice.name);
				ctrl.subtitle = conf.header?.subtitle ?? ctrl.clDevice.type;
				ctrl.image = conf.image;
				ctrl.content = ctrl.prepareForInterpolate(
					conf.content,
					'Please add widget content'
				);

				for (const footer of conf.footer || []) {
					ctrl.footer.push({
						icon: footer?.icon,
						label: $interpolate(ctrl.prepareForInterpolate(footer?.label))(
							$scope
						),
						click: footer?.action && ctrl.getActionClick(footer.action),
						class: footer?.class,
						tooltip: footer?.tooltip,
						condition: ctrl.prepareCondition(footer.condition),
					});
				}
			};

			ctrl.prepareCondition = function (condition) {
				if (!condition) {
					return () => true;
				}

				const variable = condition.variable.replace(
					ctrl.deviceRegexp,
					'clDevice.'
				);
				const operator = condition.operator ?? '===';
				const value = condition.value;

				return $parse('' + variable + ' ' + operator + ' ' + value);
			};

			ctrl.prepareForInterpolate = function (str, defaultStr = '') {
				if (!str?.length) {
					return defaultStr;
				}
				return str.replace(ctrl.deviceRegexp, '$ctrl.clDevice.');
			};

			ctrl.getActionClick = function (action) {
				return () => {
					const uuidParamName = action.uuid ?? 'uuid';
					const params = {
						[uuidParamName]: ctrl.clDevice.uuid,
					};
					rpcService
						.sendCommand(action.command, action.to, params, action.timeout)
						.then((resp) => {
							cleepService.reloadDevices();
						});
				};
			};

			ctrl.getContent = function () {
				if (!ctrl.content?.length) {
					return '';
				}
				return $interpolate(ctrl.content)($scope);
			};
		},
	],
});
