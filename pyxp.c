#include <Python.h>
#include "structmember.h"
#include <string.h>

#include <ixp.h>

typedef struct {
    PyObject_HEAD
        PyObject *address;
    IxpClient *client;
} Wmii;

static int Wmii_init(Wmii *self, PyObject *args, PyObject *kwds);
static void Wmii_dealloc(Wmii *self);
static PyObject *Wmii_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

static PyObject *Wmii_create(Wmii *self, PyObject *args);
static PyObject *Wmii_remove(Wmii *self, PyObject *args);
static PyObject *Wmii_ls(Wmii *self, PyObject *args);
static PyObject *Wmii_write(Wmii *self, PyObject *args);
static PyObject *Wmii_read(Wmii *self, PyObject *args);

static PyMemberDef Wmii_members[] = {
    { "address", T_OBJECT_EX, offsetof(Wmii, address), 0, "client address" },
    {NULL}
};

static PyMethodDef Wmii_methods[] = {
    {"ls", (PyCFunction)Wmii_ls, METH_VARARGS,
        "Return the listing of a path."},
    {"read", (PyCFunction)Wmii_read, METH_VARARGS,
        "Return the contents of a file."},
    {"write", (PyCFunction)Wmii_write, METH_VARARGS,
        "Write to a file."},
    {"create", (PyCFunction)Wmii_create, METH_VARARGS,
        "Create a file."},
    {"remove", (PyCFunction)Wmii_remove, METH_VARARGS,
        "Remove a file."},
    {NULL},
};

    static PyTypeObject WmiiType = {
        PyObject_HEAD_INIT(NULL)
            0,                         /*ob_size*/
        "pyxp.Wmii",               /*tp_name*/
        sizeof(Wmii),         /*tp_basicsize*/
        0,                         /*tp_itemsize*/
        (destructor)Wmii_dealloc,  /*tp_dealloc*/
        0,                         /*tp_print*/
        0,                         /*tp_getattr*/
        0,                         /*tp_setattr*/
        0,                         /*tp_compare*/
        0,                         /*tp_repr*/
        0,                         /*tp_as_number*/
        0,                         /*tp_as_sequence*/
        0,                         /*tp_as_mapping*/
        0,                         /*tp_hash */
        0,                         /*tp_call*/
        0,                         /*tp_str*/
        0,                         /*tp_getattro*/
        0,                         /*tp_setattro*/
        0,                         /*tp_as_buffer*/
        Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /*tp_flags*/
        "WMII objects",            /* tp_doc */
        0,                         /* tp_traverse */
        0,                         /* tp_clear */
        0,                         /* tp_richcompare */
        0,                         /* tp_weaklistoffset */
        0,                         /* tp_iter */
        0,                         /* tp_iternext */
        Wmii_methods,                         /* tp_methods */
        Wmii_members,              /* tp_members */
        0,                         /* tp_getset */
        0,                         /* tp_base */
        0,                         /* tp_dict */
        0,                         /* tp_descr_get */
        0,                         /* tp_descr_set */
        0,                         /* tp_dictoffset */
        (initproc)Wmii_init,       /* tp_init */
        0,                         /* tp_alloc */
        Wmii_new,                  /* tp_new */
    };

    PyMODINIT_FUNC
initpyxp(void)
{
    PyObject *m;

    if (PyType_Ready(&WmiiType) < 0)
        return;

    m =  Py_InitModule3("pyxp", NULL, "Python libixp module");

    if (m==NULL)
        return;

    Py_INCREF(&WmiiType);
    PyModule_AddObject(m, "Wmii", (PyObject *)&WmiiType);
}

    static PyObject *
Wmii_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    Wmii *self;

    self = (Wmii *)type->tp_alloc(type, 0);
    if (self != NULL) {
        self->client = NULL;
        self->address = NULL;
    }
    else
    {
        printf("Error creating object!\n");
    }
    //printf("self->client: %d\n", self->client);

    return (PyObject *)self;
}

static PyObject *
Wmii_create(Wmii *self, PyObject *args)
{
    IxpCFid *fid;
    const char *file;
    const char *data;

    if (!PyArg_ParseTuple(args, "s|s", &file, &data)) {
        PyErr_SetString(PyExc_TypeError, "Wmii.create() requires 1 argument");
        return NULL;
    }

    fid = ixp_create(self->client, file, 0777, P9_OWRITE);
    if(fid == NULL)
    {
        PyErr_SetObject(PyExc_IOError, PyString_FromFormat("Can't create file '%s'\n", file));
    }

    if((fid->qid.type&P9_DMDIR) == 0)
    {
        if(strlen(data)) {
            ixp_write(fid, data, strlen(data));
        }
    }
    ixp_close(fid);
    Py_RETURN_NONE;
}

static PyObject *
Wmii_remove(Wmii *self, PyObject *args)
{
    const char *file;

    if (!PyArg_ParseTuple(args, "s", &file)) {
        PyErr_SetString(PyExc_TypeError, "Wmii.remove() takes exactly 1 argument");
        return NULL;
    }

    if (!ixp_remove(self->client, file))
    {
        PyErr_SetObject(PyExc_IOError, PyString_FromFormat("Can't remove file '%s'\n", file));
        return NULL;
    }
    Py_RETURN_NONE;
}

static PyObject *
Wmii_write(Wmii *self, PyObject *args)
{
    const char *file;
    const char *data;

    IxpCFid *fid;

    if (!PyArg_ParseTuple(args, "ss", &file,  &data)) {
        PyErr_SetString(PyExc_TypeError, "Wmii.write() takes exactly 2 arguments");
        return NULL;
    }

    fid = ixp_open(self->client, file, P9_OWRITE);
    if(fid == NULL)
    {
        PyErr_SetObject(PyExc_IOError, PyString_FromFormat("Can't open file '%s'\n", file));
        return NULL;
    }

    ixp_write(fid, data, strlen(data));

    ixp_close(fid);

    Py_RETURN_NONE;
}

static PyObject *
Wmii_read(Wmii *self, PyObject *args)
{
    const char *file;

    char *readbuf;
    unsigned int count = 1;

    char *buf;
    unsigned int len;
    unsigned int size;

    PyObject *outstr;

    IxpCFid *fid;

    PyArg_ParseTuple(args, "s", &file);

    fid = ixp_open(self->client, file, P9_OREAD);

    readbuf = malloc(fid->iounit);

    len = 1;
    size = fid->iounit;
    buf = malloc(size);
    buf[0] = '\0';

    while( (count = ixp_read(fid, readbuf, fid->iounit)) > 0 )
    {
        while( (len+count) > size )
        {
            size <<= 1;
            buf = realloc(buf, size);
        }
        strcpy(&buf[len-1], readbuf);
        len += count;
    }

    ixp_close(fid);
    outstr = PyString_FromString(buf);

    free(buf);
    free(readbuf);

    return outstr;

}

static PyObject *
Wmii_ls(Wmii *self, PyObject *args)
{
    const char *file;
    char *buf;
    PyArg_ParseTuple(args, "s", &file);
    int count;
    PyObject *list;

    IxpCFid *fid;
    IxpStat stat;
    IxpMsg msg;

    fid = ixp_open(self->client, file, P9_OREAD);
    buf = malloc(fid->iounit);

    list = PyList_New(0);

    while( (count = ixp_read(fid, buf, fid->iounit)) > 0 )
    {

        msg = ixp_message(buf, count, MsgUnpack);
        while(msg.pos < msg.end)
        {
            ixp_pstat(&msg, &stat);
            PyList_Append(list, PyString_FromString(stat.name));
        }
    }

    ixp_close(fid);
    free(buf);
    return list;
}

static int
Wmii_init(Wmii *self, PyObject *args, PyObject *kwds)
{
    PyObject *address, *tmp;
    const char *adr;

    if (!PyArg_ParseTuple(args, "S", &address))
        return -1;

    if(address) {
        if (self->client) {
            ixp_unmount(self->client);
        }

        tmp = self->address;
        Py_INCREF(address);
        self->address = address;

        adr = PyString_AsString(address);


        //printf("** Wmii([%s]) **\n", adr);
        self->client = ixp_mount(adr);
        //printf("self->client: %d\n", self->client);
        if(!self->client) {
            PyErr_SetString(PyExc_RuntimeError, "Could not connect to server");
            return -1;
        }

        Py_XDECREF(tmp);
    }

    return 0;
}

static void
Wmii_dealloc(Wmii *self)
{
    if (self->client)
    {
        ixp_unmount(self->client);
    }
    Py_XDECREF(self->address);
    self->ob_type->tp_free((PyObject*)self);
}
