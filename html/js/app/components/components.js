angular
.module('Cleep')
.directive('componentsDirective', [
function() {

    var componentsController = function($interval) {
        var self = this;
        self.meta = { test: 'some data' , value: 666 };
        self.textContent = 'Some text content';
        self.htmlContent = 'Some html content<br><ul><li>bullet #1</li><li>bullet #2</li></ul>';
        self.markdownContent = 'Some markdown **bold** [link](https://google.com)';
        self.inputNumber = 8;
        self.inputText = 'text';
        self.inputSlider = 2;
        self.inputCheckbox = true;
        self.inputSwitch = false;
        self.selectOptions = [
            {label: 'option1', value: 'label1'},
            {label: 'option2', value: 'label2', disabled: true},
            {label: 'option3', value: 'label3', disabled: false},
            {label: 'option4', value: 'label4'},
        ];
        self.inputSelect = 'label1';
        self.inputSelects = ['label1', 'label3'];
        self.inputTime = new Date();
        self.inputDate = new Date();
        self.progress = 0;
        self.chips = ['chip1', 'chip2', 'chip3'];
        
        self.onClick = function(value, meta) {
            console.log('click parameters', { value, meta });
        };

        self.onSelect = function(current, index, selections, event) {
            console.log('click select', { current, index, selections, event });
        };

        self.onSelectChange = function(valueOrValues, event) {
            console.log('On select change', { valueOrValues, event });
        };

        self.twoButtons = [
            {color: 'md-primary', icon: 'account', label: 'account', tooltip: 'Account'},
            {color: 'md-primary', icon: 'account-alert', label: 'account-alert', disabled:true}
        ];
        self.fourButtons = [
            {color: 'md-primary', icon: 'account', label: 'account', tooltip: 'Account', click: self.onClick, meta: self.meta},
            {color: 'md-primary', icon: 'account-alert', label: 'account-alert', tooltip: 'Account-alert', disabled:true},
            {color: 'md-accent', icon: 'account-arrow-down', label: 'account-arrow-down', tooltip: 'Account-arrow-down'},
            {color: 'md-warn', icon: 'account-badge', label: 'account-badge', tooltip: 'Account-badge'},
        ];

        self.listItems = [
            {
                title: 'item1',
                subtitle: 'description1',
                icon: 'alert',
                iconClass: 'md-primary',
                meta: { item: 'meta' },
                clicks:[
                    { tooltip: 'Delete', icon: 'delete', class:'md-accent', click: self.onClick },
                    { tooltip: 'Hat', icon: 'account-cowboy-hat', click: self.onClick, meta: { value: 'dummy', click: 'meta' } },
                ],
            }
        ]

        self.updateProgress = function() {
            self.progress += 10;
            if (self.progress>=100) {
                self.progress = 0;
            }
        };
        $interval(self.updateProgress, 1000);
    };

    return {
        templateUrl: 'js/app/components/components.html',
        replace: true,
        scope: true,
        controller: ['$interval', componentsController],
        controllerAs: '$ctrl'
    };
}]);
