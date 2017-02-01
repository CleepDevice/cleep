var rpcService = function($http, $q, toast, $base64) {
    var self = this;
    self.uriCommand = window.location.protocol + '//' + window.location.host + '/command';
    self.uriPoll = window.location.protocol + '//' + window.location.host + '/poll';
    self.uriRegisterPoll = window.location.protocol + '//' + window.location.host + '/registerpoll';
    self.uriModules = window.location.protocol + '//' + window.location.host + '/modules';
    self.pollKey = null;

    /**
     * send command
     * @param data: data to send
     * @param to: request destinated to specified module. If not specified
     *            message will be broadcasted to all modules
     * @return promises
     */
    self.sendCommand = function(command, to, params) {
        var d = $q.defer();
        var data = {};

        //prepare data
        data.command = command;
        if( params!==undefined && params!==null ) {
            data.params = params;
        }
        else {
            //no params
            data.params = {}
        }
        if( to!==undefined && to!==null ) {
            //push command
            data.to = to;
        }
        else {
            //broadcast command
            data.to = null;
        }

        $http({
            method: 'POST',
            url: self.uriCommand,
            data: data,
            responseType:'json'
        })
        .then(function(resp) {
            if( resp.data.error ) {
                console.error('Request failed: '+resp.data.message);
                toast.error(resp.data.message);
                d.reject('request failed');
            }
            else {
                //display message if provided
                if( resp.data.message ) {
                    toast.succes(resp.data.message);
                }
                d.resolve(resp.data);
            }
        }, function(err) {
            console.error('Request failed: '+err);
            d.reject('request failed');
        });

        return d.promise;
    };

    /**
     * Get loaded modules server side
     */
    self.getModules = function() {
        var d = $q.defer();

        $http({
            method: 'POST',
            url: self.uriModules,
            responseType: 'json'
        })
        .then(function(resp) {
            if( resp.data.error ) {
                console.error('Request failed: '+resp.data.message);
                toast.error(resp.data.message);
                d.reject('request failed');
            }
            else {
                d.resolve(resp.data);
            }
        }, function(err) {
            console.error('Request failed: '+err);
            d.reject('request failed');
        });

        return d.promise;
    };

    /**
     * Poll
     */
    self.poll = function()
    {
        if( self.pollKey===null )
        {
            //not registered yet to server, get poll key
            return self.__registerPoll();
        }
        else
        {
            //already registered
            return self.__poll();
        }
    }

    /**
     * Poll
     */
    self.__poll = function()
    {
        var d = $q.defer();

        $http({
            method: 'POST',
            data: {'pollKey': self.pollKey},
            url: self.uriPoll,
            responseType:'json'
        })
        .then(function(resp) {
            if( resp && resp.data.error!==undefined && resp.data.error===true )
            {
                //error occured
                if( resp.data.message==='Client not registered' )
                {
                    //reset poll key
                    self.pollKey = null;
                }
                d.reject(resp.message);
            }
            else
            {
                d.resolve(resp.data);
            }
        }, function(resp) {
            d.reject('Connection problem');
        });

        return d.promise;
    };

    /**
     * Register polling
     */
    self.__registerPoll = function()
    {
        var d = $q.defer();

        $http({
            method: 'POST',
            url: self.uriRegisterPoll,
            responseType: 'json'
        })
        .then(function(resp) {
            self.pollKey = resp.data.pollKey;
            d.resolve('registered');
        }, function(resp) {
            d.reject('Connection problem');
        });

        return d.promise;
    };
};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('rpcService', ['$http', '$q', 'toastService', '$base64', rpcService]);

