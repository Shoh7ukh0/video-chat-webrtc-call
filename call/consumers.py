# call/consumers.py
import json
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer

from accounts.models import ActiveUser


class CallConsumer(WebsocketConsumer):
    def connect(self):
        self.accept()
        if self.scope['url_route']['kwargs'].get('is_admin', False):
            ActiveUser.objects.get_or_create(username=f"{self.scope['url_route']['kwargs']['username']}", is_admin=True)
            self.notify_other_users_disconnected()
        else:
            ActiveUser.objects.get_or_create(username=f"{self.scope['url_route']['kwargs']['username']}")
        # response to client, that we are connected.
        active_admins = ActiveUser.objects.filter(is_admin=True).values_list('username', flat=True)
        # active_admins = ActiveUser.objects.all().values_list('username', flat=True)
        self.send(text_data=json.dumps({
            'type': 'connection',
            'data': {
                'message': "Connected",
                # 'active_admins': list(active_admins),
                'active_admins': [] if self.scope['url_route']['kwargs'].get('is_admin', False) else list(active_admins),
            }
        }))

    def disconnect(self, close_code):
        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(
            self.my_name,
            self.channel_name
        )
        ActiveUser.objects.filter(username=self.my_name).delete()
        self.notify_other_users_disconnected()
        
        
    # Receive message from client WebSocket
    def receive(self, text_data):
        text_data_json = json.loads(text_data)
        # print(text_data_json)

        eventType = text_data_json['type']

        if eventType == 'login':
            name = text_data_json['data']['name']

            # we will use this as room name as well
            self.my_name = name

            # Join room
            async_to_sync(self.channel_layer.group_add)(
                self.my_name,
                self.channel_name
            )
        
        if eventType == 'call':
            name = text_data_json['data']['name']
            print(self.my_name, "is calling", name);
            # print(text_data_json)


            # to notify the callee we sent an event to the group name
            # and their's groun name is the name
            async_to_sync(self.channel_layer.group_send)(
                name,
                {
                    'type': 'call_received',
                    'data': {
                        'caller': self.my_name,
                        'rtcMessage': text_data_json['data']['rtcMessage']
                    }
                }
            )

        if eventType == 'answer_call':
            # has received call from someone now notify the calling user
            # we can notify to the group with the caller name
            
            caller = text_data_json['data']['caller']
            # print(self.my_name, "is answering", caller, "calls.")

            async_to_sync(self.channel_layer.group_send)(
                caller,
                {
                    'type': 'call_answered',
                    'data': {
                        'rtcMessage': text_data_json['data']['rtcMessage']
                    }
                }
            )

        if eventType == 'ICEcandidate':

            user = text_data_json['data']['user']

            async_to_sync(self.channel_layer.group_send)(
                user,
                {
                    'type': 'ICEcandidate',
                    'data': {
                        'rtcMessage': text_data_json['data']['rtcMessage']
                    }
                }
            )
            
        if eventType == 'admin_connected':
            users = ActiveUser.objects.all()
            active_admins = users.filter(is_admin=True).values_list('username', flat=True)
            active_users = users.filter(is_admin=False).values_list('username', flat=True)
            for user in active_users:
                async_to_sync(self.channel_layer.group_send)(
                    user,
                    {
                        'type': 'admin_connected',
                        'data': {
                            'active_admins': list(active_admins)
                        }
                    }
                )
        if eventType == 'admin_disconnected':
            users = ActiveUser.objects.all()
            active_admins = users.filter(is_admin=True).values_list('username', flat=True)
            active_users = users.filter(is_admin=False).values_list('username', flat=True)
            for user in active_users:
                async_to_sync(self.channel_layer.group_send)(
                    user,
                    {
                        'type': 'admin_disconnected',
                        'data': {
                            'active_admins': list(active_admins)
                        }
                    }
                )
                

    def call_received(self, event):

        # print(event)
        print('Call received by ', self.my_name )
        self.send(text_data=json.dumps({
            'type': 'call_received',
            'data': event['data']
        }))


    def call_answered(self, event):

        # print(event)
        print(self.my_name, "'s call answered")
        self.send(text_data=json.dumps({
            'type': 'call_answered',
            'data': event['data']
        }))


    def ICEcandidate(self, event):
        self.send(text_data=json.dumps({
            'type': 'ICEcandidate',
            'data': event['data']
        }))
        
    def admin_connected(self, event):
        self.send(text_data=json.dumps({
            'type': 'admin_connected',
            'data': event['data']
        }))
        
    def admin_disconnected(self, event):
        self.send(text_data=json.dumps({
            'type': 'admin_disconnected',
            'data': event['data']
        }))
    
    
    def notify_other_users_connected(self):
        users = ActiveUser.objects.all()
        active_admins = users.filter(is_admin=True).values_list('username', flat=True)
        active_users = users.filter(is_admin=False).values_list('username', flat=True)
        for user in active_users:
            async_to_sync(self.channel_layer.send)(
                user,
                {
                    'type': 'admin_connected',
                    'data': {
                        'active_admins': list(active_admins)
                    }
                }
            )

    def notify_other_users_disconnected(self):
        users = ActiveUser.objects.all()
        active_admins = users.filter(is_admin=True).values_list('username', flat=True)
        active_users = users.filter(is_admin=False).values_list('username', flat=True)
        for user in active_users:
            async_to_sync(self.channel_layer.group_send)(
                user,
                {
                    'type': 'admin_disconnected',
                    'data': {
                        'active_admins': list(active_admins)
                    }
                }
            )