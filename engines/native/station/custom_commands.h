/* Validated commands, one decimal action + tab + UTF-8 phrase per line.
 * Actions 1-4 are exact. Action 5 is a prefix: the rest of the utterance is
 * the question. The question is copied only when a buffer is supplied. */
static int configured_command(const char *value, char *question, size_t size) {
    if (question && size) question[0] = 0;
    const char *path=getenv("ALISA_COMMANDS_FILE");
    if(!path||!*path)return -1;
    int fd=open(path,0);if(fd<0)return 0;
    char data[4097];long n=read(fd,data,4096);close(fd);
    if(n<=0||n>=4096)return 0;data[n]=0;
    char *line=data;
    for(long i=0;i<=n;++i)if(data[i]=='\n'||data[i]==0){
        data[i]=0;
        if(line[0]>='1'&&line[0]<='5'&&line[1]=='\t'){
            int action=line[0]-'0';
            const char *phrase=line+2;
            if(!strcmp(phrase,value))return action;
            if(action==5){
                size_t length=strlen(phrase);
                if(length&&!strncmp(value,phrase,length)&&value[length]==' '){
                    const char *rest=value+length+1;
                    while(*rest==' ')++rest;
                    if(*rest){
                        if(question&&size)snprintf(question,size,"%s",rest);
                        return 5;
                    }
                }
            }
        }
        line=data+i+1;
    }
    return 0;
}
